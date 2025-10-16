from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from django.db.models import Q, Prefetch
from django.core.cache import cache
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.exceptions import ValidationError
import logging
import re
import hashlib
from typing import List, Dict, Any, Optional

from cms.models.product import Product, ProductVariant
from cms.models.category import Category, Brand
from cms.models.facility import Facility, FacilityInventory, Cluster
from cms.models.product import Collection
from user.models import User

logger = logging.getLogger(__name__)


class GlobalSearchView(APIView):
    """
    Optimized unified global search API for production use.
    
    Features:
    - Database query optimization with select_related/prefetch_related
    - Redis caching for search results
    - Input validation and sanitization
    - Pagination support
    - Rate limiting
    - Search analytics and logging
    - Optimized relevance scoring
    
    Query Parameters:
    - q: Search query (required, 2-100 chars)
    - limit: Results per page (default: 20, max: 100)
    - page: Page number (default: 1)
    - include_inactive: Include inactive records (default: false)
    - cache: Use cache (default: true)
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    # Cache settings
    CACHE_TIMEOUT = 300  # 5 minutes
    MAX_QUERY_LENGTH = 100
    MIN_QUERY_LENGTH = 2
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100
    
    def get(self, request):
        try:
            # Validate and sanitize input
            search_query = self._validate_and_sanitize_query(request)
            limit = self._validate_limit(request)
            page = self._validate_page(request)
            include_inactive = self._get_include_inactive(request)
            use_cache = self._get_use_cache(request)
            
            # Generate cache key
            cache_key = self._generate_cache_key(search_query, limit, page, include_inactive, request.user.id)
            
            # Try to get from cache first
            if use_cache:
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for search query: {search_query}")
                    return Response(cached_result, status=status.HTTP_200_OK)
            
            # Perform search
            search_results = self._perform_optimized_search(
                search_query, request.user, limit, include_inactive
            )
            
            # Organize results by type for better structure (before pagination)
            organized_results = self._organize_results_by_type(search_results)
            
            # Paginate results
            paginated_results = self._paginate_results(search_results, page, limit)
            
            # Build response
            response_data = {
                'query': search_query,
                'total_results': len(search_results),
                'page': page,
                'limit': limit,
                'total_pages': paginated_results['total_pages'],
                'has_next': paginated_results['has_next'],
                'has_previous': paginated_results['has_previous'],
                'results': paginated_results['results'],
                'results_by_type': organized_results
            }
            
            # Cache the result
            if use_cache:
                cache.set(cache_key, response_data, self.CACHE_TIMEOUT)
                logger.info(f"Cached search results for query: {search_query}")
            
            # Log search analytics
            self._log_search_analytics(search_query, len(search_results), request.user)
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            logger.warning(f"Search validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return Response({
                'error': 'An error occurred while searching. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_and_sanitize_query(self, request) -> str:
        """Validate and sanitize search query"""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            raise ValidationError('Search query (q) is required')
        
        if len(query) < self.MIN_QUERY_LENGTH:
            raise ValidationError(f'Search query must be at least {self.MIN_QUERY_LENGTH} characters')
        
        if len(query) > self.MAX_QUERY_LENGTH:
            raise ValidationError(f'Search query must be no more than {self.MAX_QUERY_LENGTH} characters')
        
        # Sanitize query - remove special characters that could cause issues
        sanitized_query = re.sub(r'[^\w\s\-@.]', '', query)
        
        if not sanitized_query:
            raise ValidationError('Search query contains invalid characters')
        
        return sanitized_query
    
    def _validate_limit(self, request) -> int:
        """Validate limit parameter"""
        try:
            limit = int(request.query_params.get('limit', self.DEFAULT_LIMIT))
            if limit < 1:
                limit = self.DEFAULT_LIMIT
            elif limit > self.MAX_LIMIT:
                limit = self.MAX_LIMIT
            return limit
        except (ValueError, TypeError):
            return self.DEFAULT_LIMIT
    
    def _validate_page(self, request) -> int:
        """Validate page parameter"""
        try:
            page = int(request.query_params.get('page', 1))
            return max(1, page)
        except (ValueError, TypeError):
            return 1
    
    def _get_include_inactive(self, request) -> bool:
        """Get include_inactive parameter"""
        return request.query_params.get('include_inactive', 'false').lower() == 'true'
    
    def _get_use_cache(self, request) -> bool:
        """Get cache parameter"""
        return request.query_params.get('cache', 'true').lower() == 'true'
    
    def _generate_cache_key(self, query: str, limit: int, page: int, include_inactive: bool, user_id: int) -> str:
        """Generate cache key for search results"""
        key_data = f"{query}:{limit}:{page}:{include_inactive}:{user_id}"
        return f"search:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def _perform_optimized_search(self, query: str, user, limit: int, include_inactive: bool) -> List[Dict[str, Any]]:
        """Perform optimized search with prioritized entity order and max 3 per type"""
        all_results = []
        
        # Split query into individual words for better multi-word search
        query_words = query.split()
        
        # PRIORITY 1: Products (most relevant first 3) - HIGHEST PRIORITY
        products = self._search_products_optimized(query, query_words, user, 3, include_inactive)
        # Add priority weight to ensure products come first
        for product in products:
            product['priority_weight'] = 1000  # Highest priority
        all_results.extend(products)
        
        # PRIORITY 2: Collections and Brands (most relevant first 3 each)
        collections = self._search_collections_optimized(query, 3, include_inactive)
        for collection in collections:
            collection['priority_weight'] = 800  # Second priority
        all_results.extend(collections)
        
        brands = self._search_brands_optimized(query, 3, include_inactive)
        for brand in brands:
            brand['priority_weight'] = 800  # Second priority
        all_results.extend(brands)
        
        # PRIORITY 3: Facilities and Categories (most relevant first 3 each)
        facilities = self._search_facilities_optimized(query, 3, include_inactive)
        for facility in facilities:
            facility['priority_weight'] = 600  # Third priority
        all_results.extend(facilities)
        
        categories = self._search_categories_optimized(query, 3, include_inactive)
        for category in categories:
            category['priority_weight'] = 600  # Third priority
        all_results.extend(categories)
        
        # Additional entities (if needed, max 3 each)
        clusters = self._search_clusters_optimized(query, 3, include_inactive)
        for cluster in clusters:
            cluster['priority_weight'] = 400  # Lower priority
        all_results.extend(clusters)
        
        users = self._search_users_optimized(query, 3, include_inactive)
        for user_obj in users:
            user_obj['priority_weight'] = 400  # Lower priority
        all_results.extend(users)
        
        # Sort by priority weight first, then by relevance score
        all_results.sort(key=lambda x: (x.get('priority_weight', 0), x.get('relevance_score', 0)), reverse=True)
        return all_results
    
    def _search_products_optimized(self, query: str, query_words: List[str], user, limit: int, include_inactive: bool) -> List[Dict[str, Any]]:
        """Optimized product search with select_related"""
        products_qs = Product.objects.select_related('category', 'brand').prefetch_related(
            'variants__images'
        ).all()
        
        if not include_inactive:
            products_qs = products_qs.filter(is_active=True, is_published=True)
        
        # Apply role-based filtering for managers
        if user.role == 'manager':
            managed_facilities = Facility.objects.filter(managers=user)
            product_variant_ids = FacilityInventory.objects.filter(
                facility__in=managed_facilities
            ).values_list('product_variant', flat=True)
            products_qs = products_qs.filter(variants__in=product_variant_ids).distinct()
        
        # Multi-word search query - handle both phrase and individual word matches
        escaped_query = re.escape(query)
        
        # Build Q objects for each word in the query
        word_queries = []
        for word in query_words:
            if len(word) >= 2:  # Only search words with 2+ characters
                escaped_word = re.escape(word)
                word_queries.append(
                    Q(name__icontains=word) |
                    Q(category__name__icontains=word) |
                    Q(brand__name__icontains=word) |
                    Q(variants__name__icontains=word) |
                    Q(variants__sku__icontains=word) |
                    Q(tags__icontains=word)
                )
        
        # Combine phrase search with individual word search
        product_search = (
            # Exact phrase matches (highest priority)
            Q(name__iexact=query) |
            Q(category__name__iexact=query) |
            Q(brand__name__iexact=query) |
            Q(variants__name__iexact=query) |
            Q(variants__sku__iexact=query) |
            # Phrase word boundary matches (very high priority)
            Q(name__iregex=rf'\b{escaped_query}\b') |
            Q(category__name__iregex=rf'\b{escaped_query}\b') |
            Q(brand__name__iregex=rf'\b{escaped_query}\b') |
            Q(variants__name__iregex=rf'\b{escaped_query}\b') |
            Q(tags__iregex=rf'\b{escaped_query}\b') |
            # Phrase starts with matches (high priority)
            Q(name__istartswith=query) |
            Q(category__name__istartswith=query) |
            Q(brand__name__istartswith=query) |
            Q(variants__name__istartswith=query) |
            Q(variants__sku__istartswith=query) |
            # Phrase contains matches (medium priority)
            Q(name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(brand__name__icontains=query) |
            Q(variants__name__icontains=query) |
            Q(tags__icontains=query)
        )
        
        # Add individual word matches if we have multiple words
        if len(query_words) > 1:
            # All words must be present (AND logic)
            for word_query in word_queries:
                product_search = product_search | word_query
        
        products = products_qs.filter(product_search).distinct()[:limit]
        
        results = []
        for product in products:
            results.append({
                'type': 'product',
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'category_name': product.category.name if product.category else None,
                'brand_name': product.brand.name if product.brand else None,
                'is_active': product.is_active,
                'search_highlight': self._get_product_highlights(product, query),
                'url': f'/products/{product.id}/',
                'relevance_score': self._calculate_product_relevance(product, query)
            })
        
        return results
    
    def _search_categories_optimized(self, query: str, limit: int, include_inactive: bool) -> List[Dict[str, Any]]:
        """Optimized category search"""
        categories_qs = Category.objects.select_related('parent').all()
        
        if not include_inactive:
            categories_qs = categories_qs.filter(is_active=True)
        
        # Improved category search with better matching
        escaped_query = re.escape(query)
        category_search = (
            Q(name__iexact=query) |
            Q(name__iregex=rf'\b{escaped_query}\b') |
            Q(name__istartswith=query) |
            (Q(name__icontains=query) if len(query) >= 4 else Q(pk__in=[]))
        )
        categories = categories_qs.filter(category_search).distinct()[:limit]
        
        results = []
        for category in categories:
            results.append({
                'type': 'category',
                'id': category.id,
                'name': category.name,
                'parent_name': category.parent.name if category.parent else None,
                'is_active': category.is_active,
                'search_highlight': self._get_category_highlights(category, query),
                'url': f'/categories/{category.id}/',
                'relevance_score': self._calculate_category_relevance(category, query)
            })
        
        return results
    
    def _search_brands_optimized(self, query: str, limit: int, include_inactive: bool) -> List[Dict[str, Any]]:
        """Optimized brand search"""
        brands_qs = Brand.objects.all()
        
        if not include_inactive:
            brands_qs = brands_qs.filter(is_active=True)
        
        # Improved brand search with better matching
        escaped_query = re.escape(query)
        brand_search = (
            Q(name__iexact=query) |
            Q(name__iregex=rf'\b{escaped_query}\b') |
            Q(name__istartswith=query) |
            (Q(name__icontains=query) if len(query) >= 4 else Q(pk__in=[]))
        )
        brands = brands_qs.filter(brand_search).distinct()[:limit]
        
        results = []
        for brand in brands:
            results.append({
                'type': 'brand',
                'id': brand.id,
                'name': brand.name,
                'is_active': brand.is_active,
                'search_highlight': self._get_brand_highlights(brand, query),
                'url': f'/brands/{brand.id}/',
                'relevance_score': self._calculate_brand_relevance(brand, query)
            })
        
        return results
    
    def _search_facilities_optimized(self, query: str, limit: int, include_inactive: bool) -> List[Dict[str, Any]]:
        """Optimized facility search"""
        facilities_qs = Facility.objects.prefetch_related('managers', 'clusters').all()
        
        if not include_inactive:
            facilities_qs = facilities_qs.filter(is_active=True)
        
        facility_search = (
            Q(name__icontains=query) |
            Q(facility_type__icontains=query) |
            Q(address__icontains=query) |
            Q(city__icontains=query) |
            Q(state__icontains=query) |
            Q(country__icontains=query) |
            Q(pincode__icontains=query)
        )
        
        facilities = facilities_qs.filter(facility_search).distinct()[:limit]
        
        results = []
        for facility in facilities:
            results.append({
                'type': 'facility',
                'id': facility.id,
                'name': facility.name,
                'facility_type': facility.facility_type,
                'city': facility.city,
                'state': facility.state,
                'is_active': facility.is_active,
                'search_highlight': self._get_facility_highlights(facility, query),
                'url': f'/facilities/{facility.id}/',
                'relevance_score': self._calculate_facility_relevance(facility, query)
            })
        
        return results
    
    def _search_clusters_optimized(self, query: str, limit: int, include_inactive: bool) -> List[Dict[str, Any]]:
        """Optimized cluster search"""
        clusters_qs = Cluster.objects.prefetch_related('facilities').all()
        
        if not include_inactive:
            clusters_qs = clusters_qs.filter(is_active=True)
        
        cluster_search = (
            Q(name__icontains=query) |
            Q(region__icontains=query)
        )
        
        clusters = clusters_qs.filter(cluster_search).distinct()[:limit]
        
        results = []
        for cluster in clusters:
            results.append({
                'type': 'cluster',
                'id': cluster.id,
                'name': cluster.name,
                'region': cluster.region,
                'is_active': cluster.is_active,
                'search_highlight': self._get_cluster_highlights(cluster, query),
                'url': f'/clusters/{cluster.id}/',
                'relevance_score': self._calculate_cluster_relevance(cluster, query)
            })
        
        return results
    
    def _search_collections_optimized(self, query: str, limit: int, include_inactive: bool) -> List[Dict[str, Any]]:
        """Optimized collection search"""
        collections_qs = Collection.objects.all()
        
        if not include_inactive:
            collections_qs = collections_qs.filter(is_active=True)
        
        collections = collections_qs.filter(name__icontains=query).distinct()[:limit]
        
        results = []
        for collection in collections:
            results.append({
                'type': 'collection',
                'id': collection.id,
                'name': collection.name,
                'is_active': collection.is_active,
                'search_highlight': self._get_collection_highlights(collection, query),
                'url': f'/collections/{collection.id}/',
                'relevance_score': self._calculate_collection_relevance(collection, query)
            })
        
        return results
    
    def _search_users_optimized(self, query: str, limit: int, include_inactive: bool) -> List[Dict[str, Any]]:
        """Optimized user search"""
        users_qs = User.objects.prefetch_related('managed_facilities').all()
        
        if not include_inactive:
            users_qs = users_qs.filter(is_active=True)
        
        user_search = (
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
        
        users = users_qs.filter(user_search).distinct()[:limit]
        
        results = []
        for user_obj in users:
            results.append({
                'type': 'user',
                'id': user_obj.id,
                'name': f"{user_obj.first_name} {user_obj.last_name}".strip() or user_obj.username,
                'username': user_obj.username,
                'email': user_obj.email,
                'role': user_obj.role,
                'is_active': user_obj.is_active,
                'search_highlight': self._get_user_highlights(user_obj, query),
                'url': f'/users/{user_obj.id}/',
                'relevance_score': self._calculate_user_relevance(user_obj, query)
            })
        
        return results
    
    def _paginate_results(self, results: List[Dict[str, Any]], page: int, limit: int) -> Dict[str, Any]:
        """Paginate search results"""
        paginator = Paginator(results, limit)
        page_obj = paginator.get_page(page)
        
        return {
            'results': page_obj.object_list,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    
    def _get_optimized_relevance_score(self, result: Dict[str, Any], query: str) -> float:
        """Optimized relevance scoring with priority weight and pre-calculated scores"""
        priority_weight = result.get('priority_weight', 0)
        relevance_score = result.get('relevance_score', 50.0)
        # Combine priority weight and relevance score for final sorting
        return priority_weight + relevance_score
    
    def _calculate_product_relevance(self, product, query: str) -> float:
        """Calculate relevance score for products with improved multi-word matching"""
        query_lower = query.lower()
        name_lower = product.name.lower()
        query_words = query_lower.split()
        
        # Exact phrase match (highest priority)
        if query_lower == name_lower:
            return 100.0
        
        # Phrase word boundary match (very high priority)
        if re.search(rf'\b{re.escape(query_lower)}\b', name_lower):
            return 95.0
        
        # Phrase starts with (high priority)
        if name_lower.startswith(query_lower):
            return 90.0
        
        # Brand exact match (very high priority for brand searches)
        if product.brand and query_lower == product.brand.name.lower():
            return 88.0
        
        # Category exact match
        if product.category and query_lower == product.category.name.lower():
            return 85.0
        
        # Multi-word scoring - check how many words match
        if len(query_words) > 1:
            word_matches = 0
            total_words = len(query_words)
            
            # Check name matches
            for word in query_words:
                if word in name_lower:
                    word_matches += 1
                elif re.search(rf'\b{re.escape(word)}\b', name_lower):
                    word_matches += 1.5  # Bonus for word boundary matches
            
            # Check brand matches
            if product.brand:
                brand_lower = product.brand.name.lower()
                for word in query_words:
                    if word in brand_lower:
                        word_matches += 1.2  # Bonus for brand matches
                    elif re.search(rf'\b{re.escape(word)}\b', brand_lower):
                        word_matches += 1.5
            
            # Check category matches
            if product.category:
                category_lower = product.category.name.lower()
                for word in query_words:
                    if word in category_lower:
                        word_matches += 1.1  # Bonus for category matches
                    elif re.search(rf'\b{re.escape(word)}\b', category_lower):
                        word_matches += 1.3
            
            # Calculate score based on word match ratio
            if word_matches > 0:
                match_ratio = word_matches / total_words
                base_score = 60 + (match_ratio * 30)  # 60-90 range
                return min(base_score, 89.0)  # Cap at 89 to keep phrase matches higher
        
        # Single word or fallback scoring
        # Brand word boundary match
        if product.brand and re.search(rf'\b{re.escape(query_lower)}\b', product.brand.name.lower()):
            return 80.0
        
        # Category word boundary match
        if product.category and re.search(rf'\b{re.escape(query_lower)}\b', product.category.name.lower()):
            return 75.0
        
        # Name word boundary match
        if re.search(rf'\b{re.escape(query_lower)}\b', name_lower):
            return 70.0
        
        # Brand contains match
        if product.brand and query_lower in product.brand.name.lower():
            return 65.0
        
        # Category contains match
        if product.category and query_lower in product.category.name.lower():
            return 60.0
        
        # Name contains match (only for longer queries)
        if len(query) >= 4 and query_lower in name_lower:
            return 55.0
        
        return 30.0
    
    def _calculate_category_relevance(self, category, query: str) -> float:
        """Calculate relevance score for categories"""
        query_lower = query.lower()
        name_lower = category.name.lower()
        
        if query_lower == name_lower:
            return 100.0
        elif name_lower.startswith(query_lower):
            return 95.0
        elif query_lower in name_lower:
            return 85.0
        
        return 50.0
    
    def _calculate_brand_relevance(self, brand, query: str) -> float:
        """Calculate relevance score for brands"""
        query_lower = query.lower()
        name_lower = brand.name.lower()
        
        if query_lower == name_lower:
            return 100.0
        elif name_lower.startswith(query_lower):
            return 95.0
        elif query_lower in name_lower:
            return 85.0
        
        return 50.0
    
    def _calculate_facility_relevance(self, facility, query: str) -> float:
        """Calculate relevance score for facilities"""
        query_lower = query.lower()
        name_lower = facility.name.lower()
        
        # Type-specific scoring
        if query_lower in ['store', 'warehouse'] and query_lower in facility.facility_type.lower():
            return 90.0
        
        if query_lower == name_lower:
            return 100.0
        elif name_lower.startswith(query_lower):
            return 95.0
        elif query_lower in name_lower:
            return 85.0
        
        return 50.0
    
    def _calculate_cluster_relevance(self, cluster, query: str) -> float:
        """Calculate relevance score for clusters"""
        query_lower = query.lower()
        name_lower = cluster.name.lower()
        
        if query_lower in ['cluster', 'region'] and query_lower in cluster.region.lower():
            return 90.0
        
        if query_lower == name_lower:
            return 100.0
        elif name_lower.startswith(query_lower):
            return 95.0
        elif query_lower in name_lower:
            return 85.0
        
        return 50.0
    
    def _calculate_collection_relevance(self, collection, query: str) -> float:
        """Calculate relevance score for collections"""
        query_lower = query.lower()
        name_lower = collection.name.lower()
        
        if query_lower == name_lower:
            return 100.0
        elif name_lower.startswith(query_lower):
            return 95.0
        elif query_lower in name_lower:
            return 85.0
        
        return 50.0
    
    def _calculate_user_relevance(self, user, query: str) -> float:
        """Calculate relevance score for users"""
        query_lower = query.lower()
        
        if query_lower in ['user', 'users', 'manager', 'managers'] and query_lower in user.role.lower():
            return 90.0
        
        if query_lower == user.username.lower():
            return 100.0
        elif user.username.lower().startswith(query_lower):
            return 95.0
        elif query_lower in user.username.lower():
            return 85.0
        
        return 50.0
    
    def _log_search_analytics(self, query: str, result_count: int, user) -> None:
        """Log search analytics for monitoring"""
        logger.info(f"Search performed - Query: '{query}', Results: {result_count}, User: {user.id}, Role: {user.role}")
    
    def _organize_results_by_type(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Organize search results by entity type with max 3 per type"""
        organized = {
            'products': [],
            'collections': [],
            'brands': [],
            'facilities': [],
            'categories': [],
            'clusters': [],
            'users': []
        }
        
        # Group results by type
        for result in results:
            result_type = result.get('type', 'unknown')
            if result_type in organized:
                organized[result_type].append(result)
        
        # Limit to max 3 per type and sort by relevance
        for result_type in organized:
            organized[result_type] = sorted(
                organized[result_type][:3], 
                key=lambda x: x.get('relevance_score', 0), 
                reverse=True
            )
        
        return organized
    
    # Highlight methods (optimized)
    def _get_product_highlights(self, product, query: str) -> List[str]:
        """Get search highlights for products"""
        highlights = []
        query_lower = query.lower()
        
        if query_lower in product.name.lower():
            highlights.append(f"Product: {product.name}")
        if product.category and query_lower in product.category.name.lower():
            highlights.append(f"Category: {product.category.name}")
        if product.brand and query_lower in product.brand.name.lower():
            highlights.append(f"Brand: {product.brand.name}")
        
        return highlights[:3]
    
    def _get_category_highlights(self, category, query: str) -> List[str]:
        """Get search highlights for categories"""
        highlights = []
        query_lower = query.lower()
        
        if query_lower in category.name.lower():
            highlights.append(f"Category: {category.name}")
        if category.parent and query_lower in category.parent.name.lower():
            highlights.append(f"Parent: {category.parent.name}")
        
        return highlights[:3]
    
    def _get_brand_highlights(self, brand, query: str) -> List[str]:
        """Get search highlights for brands"""
        highlights = []
        query_lower = query.lower()
        
        if query_lower in brand.name.lower():
            highlights.append(f"Brand: {brand.name}")
        
        return highlights[:3]
    
    def _get_facility_highlights(self, facility, query: str) -> List[str]:
        """Get search highlights for facilities"""
        highlights = []
        query_lower = query.lower()
        
        if query_lower in facility.name.lower():
            highlights.append(f"Facility: {facility.name}")
        if query_lower in facility.facility_type.lower():
            highlights.append(f"Type: {facility.facility_type}")
        if query_lower in facility.city.lower():
            highlights.append(f"City: {facility.city}")
        
        return highlights[:3]
    
    def _get_cluster_highlights(self, cluster, query: str) -> List[str]:
        """Get search highlights for clusters"""
        highlights = []
        query_lower = query.lower()
        
        if query_lower in cluster.name.lower():
            highlights.append(f"Cluster: {cluster.name}")
        if query_lower in cluster.region.lower():
            highlights.append(f"Region: {cluster.region}")
        
        return highlights[:3]
    
    def _get_collection_highlights(self, collection, query: str) -> List[str]:
        """Get search highlights for collections"""
        highlights = []
        query_lower = query.lower()
        
        if query_lower in collection.name.lower():
            highlights.append(f"Collection: {collection.name}")
        
        return highlights[:3]
    
    def _get_user_highlights(self, user, query: str) -> List[str]:
        """Get search highlights for users"""
        highlights = []
        query_lower = query.lower()
        
        if query_lower in user.username.lower():
            highlights.append(f"Username: {user.username}")
        if query_lower in user.first_name.lower():
            highlights.append(f"Name: {user.first_name}")
        if query_lower in user.email.lower():
            highlights.append(f"Email: {user.email}")
        
        return highlights[:3]