from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from cms.utils.pagination import CustomPageNumberPagination
from django_filters import rest_framework as filters
from cms.models.setting import Attribute, AttributeValue, ProductType, SizeChart, SizeMeasurement, CustomTab, CustomSection, CustomField
from cms.serializers.setting import (
    AttributeListSerializer, AttributeCreateUpdateSerializer,
    AttributeValueListSerializer, AttributeValueCreateUpdateSerializer,
    ProductTypeListSerializer, ProductTypeCreateUpdateSerializer,
    SizeChartListSerializer, SizeChartCreateUpdateSerializer,
    SizeMeasurementListSerializer, SizeMeasurementCreateUpdateSerializer,
    CustomTabListSerializer, CustomTabCreateUpdateSerializer,
    CustomSectionListSerializer, CustomSectionCreateUpdateSerializer,
    CustomFieldListSerializer, CustomFieldCreateUpdateSerializer
)
from rest_framework.decorators import action
from rest_framework.response import Response


class AttributeViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing Attributes with separate serializers
    """
    queryset = Attribute.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ['attribute_type', 'is_required', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'rank', 'creation_date']
    ordering = ['rank', 'name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AttributeCreateUpdateSerializer
        return AttributeListSerializer

    def get_queryset(self):
        return Attribute.objects.all().prefetch_related('values', 'product_types')


class AttributeValueViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing Attribute Values with separate serializers
    """
    queryset = AttributeValue.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ['attribute', 'is_active']
    search_fields = ['value']
    ordering_fields = ['value', 'rank', 'creation_date']
    ordering = ['rank', 'value']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AttributeValueCreateUpdateSerializer
        return AttributeValueListSerializer

    def get_queryset(self):
        return AttributeValue.objects.select_related('attribute')


class ProductTypeViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing Product Types with separate serializers
    """
    queryset = ProductType.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ['category', 'is_active']
    search_fields = ['category__name']
    ordering_fields = ['creation_date', 'category__name']
    ordering = ['category__name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductTypeCreateUpdateSerializer
        return ProductTypeListSerializer

    def get_queryset(self):
        return ProductType.objects.select_related('category').prefetch_related(
            'attributes', 'attributes__values'
        )
        
        
class SizeChartViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing Size Charts
    """
    queryset = SizeChart.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ['category', 'attribute', 'is_active']
    search_fields = ['name', 'description', 'category__name', 'attribute__name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SizeChartCreateUpdateSerializer
        print("Returning List Serializer")
        return SizeChartListSerializer

    def get_queryset(self):
        return SizeChart.objects.select_related('category', 'attribute').prefetch_related('measurements')


class SizeMeasurementViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing Size Measurements
    """
    queryset = SizeMeasurement.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ['size_chart', 'is_required', 'is_active']
    search_fields = ['name', 'unit']
    ordering_fields = ['name', 'rank', 'created_at']
    ordering = ['rank', 'name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SizeMeasurementCreateUpdateSerializer
        return SizeMeasurementListSerializer

    def get_queryset(self):
        return SizeMeasurement.objects.select_related('size_chart')
    

class CustomTabViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing Custom Tabs
    """
    queryset = CustomTab.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['name', 'rank', 'created_at']
    ordering = ['rank', 'name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CustomTabCreateUpdateSerializer
        return CustomTabListSerializer

    def get_queryset(self):
        return CustomTab.objects.select_related('category').prefetch_related(
            'sections', 'sections__fields'
        )

    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        """Toggle the active status of a tab"""
        tab = self.get_object()
        tab.is_active = not tab.is_active
        tab.save()
        
        serializer = self.get_serializer(tab)
        return Response({
            'message': f'Tab {"activated" if tab.is_active else "deactivated"}',
            'tab': serializer.data
        })


class CustomSectionViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing Custom Sections
    """
    queryset = CustomSection.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ['tabs', 'is_collapsed', 'is_active']
    search_fields = ['name', 'description', 'tabs__name']
    ordering_fields = ['name', 'rank', 'created_at']
    ordering = ['rank', 'name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CustomSectionCreateUpdateSerializer
        return CustomSectionListSerializer

    def get_queryset(self):
        return CustomSection.objects.prefetch_related('tabs', 'fields')


    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        """Toggle the active status of a section"""
        section = self.get_object()
        section.is_active = not section.is_active
        section.save()
        
        serializer = self.get_serializer(section)
        return Response({
            'message': f'Section {"activated" if section.is_active else "deactivated"}',
            'section': serializer.data
        })


class CustomFieldViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing Custom Fields
    """
    queryset = CustomField.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ['section', 'field_type', 'is_required', 'is_active']
    search_fields = ['name', 'label', 'help_text', 'section__name']
    ordering_fields = ['name', 'label', 'rank', 'created_at']
    ordering = ['rank', 'name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CustomFieldCreateUpdateSerializer
        return CustomFieldListSerializer

    def get_queryset(self):
        return CustomField.objects.select_related('section', 'section__tab')


    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        """Toggle the active status of a field"""
        field = self.get_object()
        field.is_active = not field.is_active
        field.save()
        
        serializer = self.get_serializer(field)
        return Response({
            'message': f'Field {"activated" if field.is_active else "deactivated"}',
            'field': serializer.data
        })