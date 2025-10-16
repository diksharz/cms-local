from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.facility import FacilityViewSet, ClusterViewSet, FacilityInventoryViewSet, FacilityProductViewSet, ClusterExportView, FacilityExportView
from .views.category import CategoryViewSet, BrandViewSet, BrandExportView, CategoryExportView
from .views.product import (
    ProductViewSet, CollectionViewSet, ProductVariantViewSet,
    ProductStatusUpdateView, BulkCreateProductsView, BulkUpdateProductsView, ProductExportView,
    ProductPricingViewSet, ProductClusterPriceUpdateView,
    ProductPriceHistoryViewSet,
    # BulkPriceUpdateView,
    OverridePriceView,
    ClusterPriceUpdateStatusView, SmartBrandBulkCreateProductsView,
    CategoryRequiredFieldsView, GS1APIView, CollectionExportView,
    ComboProductViewSet
)
from .views.upload import UploadImagesView
from .views.setting import (
    AttributeViewSet, AttributeValueViewSet, ProductTypeViewSet, SizeChartViewSet, SizeMeasurementViewSet,
    CustomTabViewSet, CustomSectionViewSet, CustomFieldViewSet
)
from .views.search import GlobalSearchView
router = DefaultRouter()
router.register(r'clusters', ClusterViewSet)
router.register(r'facilities', FacilityViewSet)
router.register(r'facilityinventory', FacilityInventoryViewSet, basename='facilityinventory')
router.register(r'facilityproducts', FacilityProductViewSet, basename='facility-product')
router.register(r'categories', CategoryViewSet)
# router.register(r'subcategories', SubcategoryViewSet)
# router.register(r'subsubcategories', SubsubcategoryViewSet)
router.register(r'brands', BrandViewSet)
router.register(r'products', ProductViewSet, basename='products')
router.register(r'collections', CollectionViewSet, basename='collections')
router.register(r'variants', ProductVariantViewSet, basename='variants')
router.register(r'combo-products', ComboProductViewSet, basename='combo-products')
router.register(r'products-pricing', ProductPricingViewSet, basename='products-pricing')
router.register(r'product-price-history', ProductPriceHistoryViewSet, basename='product-price-history')
router.register(r'attributes', AttributeViewSet, basename='attributes')
router.register(r'attribute-values', AttributeValueViewSet, basename='attribute-values')
router.register(r'product-types', ProductTypeViewSet, basename='product-types')
router.register(r'size-charts', SizeChartViewSet, basename='size-charts')
router.register(r'size-measurements', SizeMeasurementViewSet, basename='size-measurements')
router.register(r'custom-tabs', CustomTabViewSet, basename='custom-tabs')
router.register(r'custom-sections', CustomSectionViewSet, basename='custom-sections')
router.register(r'custom-fields', CustomFieldViewSet, basename='custom-fields')

urlpatterns = [
    path('products/bulk-create/', BulkCreateProductsView.as_view(), name='bulk-create-products'),
    path('products/bulk-update/', BulkUpdateProductsView.as_view(), name='bulk-update-products'),
    path('products/smart-brand-bulk-create/', SmartBrandBulkCreateProductsView.as_view(), name='smart-brand-bulk-create-products'),
    path('products/export/', ProductExportView.as_view(), name='product-export'),
    path('products/<int:product_id>/cluster-pricing/', ProductClusterPriceUpdateView.as_view(), name='product-cluster-pricing-update'),
    # path('bulk-price-update/', BulkPriceUpdateView.as_view(), name='bulk-price-update'),
    path('clusters/price-update-status/', ClusterPriceUpdateStatusView.as_view(), name='cluster-price-update-status'),
    path('categories/required-fields/', CategoryRequiredFieldsView.as_view(), name='category-required-fields'),
    path('gs1/', GS1APIView.as_view(), name='gs1-api'),
    path('brands/export/', BrandExportView.as_view(), name='brand-export'),
    path('categories/export/', CategoryExportView.as_view(), name='category-export'),
    path('collections/export/', CollectionExportView.as_view(), name='collection-export'),
    path('clusters/export/', ClusterExportView.as_view(), name='cluster-export'),
    path('override-price/', OverridePriceView.as_view(), name='override-price'),

    path('facilities/export/', FacilityExportView.as_view(), name='facility-export'),
    path('', include(router.urls)),
    path('products/<int:product_id>/status/', ProductStatusUpdateView.as_view(), name='product-status-update'),
    # path('upload/', MediaFileUploadView.as_view(), name='upload-files'),
    path("upload/", UploadImagesView.as_view(), name="upload-images"),
    path('search/', GlobalSearchView.as_view(), name='global-search'),
]
