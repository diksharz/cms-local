from rest_framework import serializers
from cms.models.setting import Attribute, AttributeValue, ProductType, ProductTypeAttribute, SizeChart, SizeMeasurement, CustomTab, CustomSection, CustomField
from cms.models.category import Category


# List/Detail Serializers (for GET operations)
class AttributeValueListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = [
            'id', 'attribute', 'value', 'is_active', 'rank'
        ]


class AttributeListSerializer(serializers.ModelSerializer):
    values = AttributeValueListSerializer(many=True, read_only=True)
    values_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Attribute
        fields = [
            'id', 'name', 'description', 'is_required', 'is_active',
            'rank', 'attribute_type', 'values', 'values_count'
        ]
    
    def get_values_count(self, obj):
        return obj.values.filter(is_active=True).count()


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductTypeListSerializer(serializers.ModelSerializer):
    category = CategoryListSerializer(read_only=True)
    attributes = serializers.SerializerMethodField()
    attributes_count = serializers.SerializerMethodField()
    required_attributes_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductType
        fields = [
            'id', 'category', 'attributes', 'attributes_count', 'required_attributes_count', 'is_active',
        ]

    def get_attributes(self, obj):
        """Return attributes with their specific values for this product type"""
        result = []
        for pta in obj.product_type_attributes.all():
            attribute_data = {
                'id': pta.attribute.id,
                'name': pta.attribute.name,
                'attribute_type': pta.attribute.attribute_type,
                'values': []
            }

            # Get specific values if they exist, otherwise get all values
            if pta.attribute_values.exists():
                attribute_data['values'] = AttributeValueListSerializer(
                    pta.attribute_values.filter(is_active=True), many=True
                ).data
            else:
                # If no specific values, return all values for this attribute
                attribute_data['values'] = AttributeValueListSerializer(
                    pta.attribute.values.filter(is_active=True), many=True
                ).data

            result.append(attribute_data)

        return result

    def get_attributes_count(self, obj):
        return obj.attributes.count()
    
    def get_required_attributes_count(self, obj):
        """Return count of required attributes for this product type"""
        return obj.attributes.filter(is_required=True).count()


# Create/Update Serializers (for POST, PUT, PATCH operations)
class AttributeValueCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = [
            'attribute', 'value', 'is_active', 'rank'
        ]
    
    def validate_value(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Value cannot be empty.")
        return value.strip()


class AttributeCreateUpdateSerializer(serializers.ModelSerializer):
    values = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of attribute values to create with the attribute"
    )
    
    class Meta:
        model = Attribute
        fields = [
            'name', 'description', 'is_required', 'is_active',
            'rank', 'attribute_type', 'values'
        ]
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip().title()
    
    def validate_values(self, values):
        """Validate the values list"""
        if not values:
            return values
        
        validated_values = []
        value_names = set()
        
        for value_data in values:
            # Check required fields
            if 'value' not in value_data and 'name' not in value_data:
                raise serializers.ValidationError("Each value must have either 'value' or 'name' field")
            
            # Use 'value' or 'name' field
            value_name = value_data.get('value') or value_data.get('name')
            if not value_name or not str(value_name).strip():
                raise serializers.ValidationError("Value name cannot be empty")
            
            value_name = str(value_name).strip()
            
            # Check for duplicates
            if value_name in value_names:
                raise serializers.ValidationError(f"Duplicate value: {value_name}")
            value_names.add(value_name)
            
            # Validate rank
            rank = value_data.get('rank', 0)
            try:
                rank = int(rank)
            except (ValueError, TypeError):
                rank = 0
            
            # Validate is_active
            is_active = value_data.get('is_active', True)
            if isinstance(is_active, str):
                is_active = is_active.lower() == 'true'
            
            validated_values.append({
                'value': value_name,
                'rank': rank,
                'is_active': bool(is_active)
            })
        
        return validated_values
    
    def create(self, validated_data):
        values_data = validated_data.pop('values', [])
        
        # Create the attribute
        attribute = Attribute.objects.create(**validated_data)
        
        # Create attribute values if provided
        if values_data:
            from django.db import transaction
            with transaction.atomic():
                for value_data in values_data:
                    AttributeValue.objects.create(
                        attribute=attribute,
                        **value_data
                    )
        
        return attribute
    
    def update(self, instance, validated_data):
        values_data = validated_data.pop('values', None)
        
        # Update attribute fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update values if provided
        if values_data is not None:
            from django.db import transaction
            with transaction.atomic():
                # Clear existing values and create new ones
                instance.values.all().delete()
                for value_data in values_data:
                    AttributeValue.objects.create(
                        attribute=instance,
                        **value_data
                    )
        
        return instance


class ProductTypeCreateUpdateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
        help_text="Single category ID (use this OR categories, not both)"
    )
    categories = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Category.objects.all()),
        write_only=True,
        required=False,
        allow_empty=False,
        help_text="List of category IDs - will create one ProductType per category"
    )
    attributes = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="List of attributes with optional specific values: [{'attribute_id': 1, 'value_ids': [1,2,3]}, ...]"
    )

    class Meta:
        model = ProductType
        fields = ['category', 'categories', 'attributes', 'is_active']
        extra_kwargs = {
            'category': {'required': False, 'allow_null': True}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure category is not required at runtime
        if 'category' in self.fields:
            self.fields['category'].required = False
            self.fields['category'].allow_null = True

    def to_internal_value(self, data):
        """Override to inject None for category if not provided but categories is"""
        # If categories is provided but not category, set category to None
        if 'categories' in data and 'category' not in data:
            data = data.copy() if hasattr(data, 'copy') else dict(data)
            data['category'] = None
        return super().to_internal_value(data)

    def validate_attributes(self, attributes):
        """Validate attributes structure"""
        if not attributes:
            return attributes

        validated_attributes = []
        for attr_data in attributes:
            # Support both old format (just IDs) and new format (dict with attribute_id and value_ids)
            if isinstance(attr_data, int):
                # Old format: just attribute ID
                validated_attributes.append({
                    'attribute_id': attr_data,
                    'value_ids': []
                })
            elif isinstance(attr_data, dict):
                # New format: attribute with specific values
                if 'attribute_id' not in attr_data:
                    raise serializers.ValidationError("Each attribute must have 'attribute_id'")

                attribute_id = attr_data['attribute_id']
                value_ids = attr_data.get('value_ids', [])

                # Validate attribute exists
                if not Attribute.objects.filter(id=attribute_id).exists():
                    raise serializers.ValidationError(f"Attribute with ID {attribute_id} does not exist")

                # Validate attribute values exist and belong to the attribute
                if value_ids:
                    valid_values = AttributeValue.objects.filter(
                        id__in=value_ids,
                        attribute_id=attribute_id
                    ).values_list('id', flat=True)

                    invalid_ids = set(value_ids) - set(valid_values)
                    if invalid_ids:
                        raise serializers.ValidationError(
                            f"Invalid attribute value IDs for attribute {attribute_id}: {list(invalid_ids)}"
                        )

                validated_attributes.append({
                    'attribute_id': attribute_id,
                    'value_ids': value_ids
                })
            else:
                raise serializers.ValidationError("Attributes must be integers or objects with 'attribute_id'")

        return validated_attributes

    def validate(self, data):
        # Check that either category or categories is provided, not both
        has_category = 'category' in data and data.get('category') is not None
        has_categories = 'categories' in data and len(data.get('categories', [])) > 0

        if has_category and has_categories:
            raise serializers.ValidationError({
                'category': 'Provide either "category" or "categories", not both.'
            })

        if not has_category and not has_categories and not self.instance:
            raise serializers.ValidationError({
                'category': 'Either "category" or "categories" is required.'
            })

        # Check unique constraint for category during updates
        if self.instance:  # This is an update
            category = data.get('category')
            if category and category != self.instance.category:
                # Check if another product type exists for this category
                if ProductType.objects.filter(category=category).exclude(pk=self.instance.pk).exists():
                    raise serializers.ValidationError({
                        'category': f'Category "{category}" already has a product type assigned. Each category can only have one product type.'
                    })
        else:  # This is a create
            # Validate single category
            if has_category:
                category = data.get('category')
                if ProductType.objects.filter(category=category).exists():
                    raise serializers.ValidationError({
                        'category': f'Category "{category}" already has a product type assigned. Each category can only have one product type.'
                    })

            # Validate multiple categories
            if has_categories:
                categories = data.get('categories')
                existing_categories = ProductType.objects.filter(
                    category__in=categories
                ).values_list('category__name', flat=True)

                if existing_categories:
                    category_names = ', '.join(existing_categories)
                    raise serializers.ValidationError({
                        'categories': f'These categories already have product types: {category_names}'
                    })

        return data

    def _create_product_type_with_attributes(self, category, is_active, attributes_data):
        """Helper method to create a product type with attributes and values"""
        from django.db import transaction

        with transaction.atomic():
            product_type = ProductType.objects.create(
                category=category,
                is_active=is_active
            )

            # Create ProductTypeAttribute entries with specific values
            for attr_data in attributes_data:
                attribute = Attribute.objects.get(id=attr_data['attribute_id'])

                # Create the ProductTypeAttribute relationship
                pta = ProductTypeAttribute.objects.create(
                    product_type=product_type,
                    attribute=attribute
                )

                # If specific values are provided, set them
                if attr_data['value_ids']:
                    pta.attribute_values.set(attr_data['value_ids'])

            return product_type

    def create(self, validated_data):
        attributes_data = validated_data.pop('attributes', [])
        categories_data = validated_data.pop('categories', None)
        is_active = validated_data.get('is_active', True)

        # If categories list is provided, create multiple ProductType records
        if categories_data:
            created_product_types = []
            for category in categories_data:
                product_type = self._create_product_type_with_attributes(
                    category, is_active, attributes_data
                )
                created_product_types.append(product_type)

            # Store all created instances for custom response handling
            self.context['created_product_types'] = created_product_types
            return created_product_types[0] if created_product_types else None
        else:
            # Single category
            category = validated_data.get('category')
            return self._create_product_type_with_attributes(
                category, is_active, attributes_data
            )

    def update(self, instance, validated_data):
        from django.db import transaction

        attributes_data = validated_data.pop('attributes', None)
        validated_data.pop('categories', None)  # Remove categories from update

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle attributes with specific values
        if attributes_data is not None:
            with transaction.atomic():
                # Clear existing ProductTypeAttribute entries
                instance.product_type_attributes.all().delete()

                # Create new ProductTypeAttribute entries
                for attr_data in attributes_data:
                    attribute = Attribute.objects.get(id=attr_data['attribute_id'])

                    pta = ProductTypeAttribute.objects.create(
                        product_type=instance,
                        attribute=attribute
                    )

                    if attr_data['value_ids']:
                        pta.attribute_values.set(attr_data['value_ids'])

        return instance
    
    

# List/Detail Serializers (for GET operations)
class SizeMeasurementListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeMeasurement
        fields = [
            'id', 'name', 'unit', 'is_required', 'is_active', 'rank'
        ]


class AttributeSimpleSerializer(serializers.ModelSerializer):
    """Simple serializer for nested attribute display in size charts"""
    values = AttributeValueListSerializer(many=True, read_only=True)
    class Meta:
        model = Attribute
        fields = ['id', 'name', 'attribute_type', 'values']


class SizeChartListSerializer(serializers.ModelSerializer):
    category = CategoryListSerializer(read_only=True)
    attribute = AttributeSimpleSerializer(read_only=True)
    measurements = SizeMeasurementListSerializer(many=True, read_only=True)
    measurements_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SizeChart
        fields = [
            'id', 'category', 'attribute', 'name', 'description', 'is_active',
            'measurements', 'measurements_count'
        ]
    
    def get_measurements_count(self, obj):
        return obj.measurements.filter(is_active=True).count()


# Create/Update Serializers (for POST/PUT/PATCH operations)
class SizeMeasurementCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeMeasurement
        fields = ['name', 'unit', 'is_required', 'is_active', 'rank']
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Measurement name cannot be empty.")
        return value.strip().title()


class SizeChartCreateUpdateSerializer(serializers.ModelSerializer):
    measurements = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of measurements for this size chart"
    )
    
    class Meta:
        model = SizeChart
        fields = ['category', 'attribute', 'name', 'description', 'is_active', 'measurements']
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()
    
    def validate(self, data):
        # Check unique constraint for category during updates
        if self.instance:  # This is an update
            category = data.get('category')
            if category and category != self.instance.category:
                if SizeChart.objects.filter(category=category).exclude(pk=self.instance.pk).exists():
                    raise serializers.ValidationError({
                        'category': f'Category "{category}" already has a size chart. Each category can only have one size chart.'
                    })
        else:  # This is a create
            category = data.get('category')
            if category:
                if SizeChart.objects.filter(category=category).exists():
                    raise serializers.ValidationError({
                        'category': f'Category "{category}" already has a size chart. Each category can only have one size chart.'
                    })
        return data
    
    def validate_measurements(self, measurements):
        """Validate measurements list"""
        if not measurements:
            return measurements
        
        validated_measurements = []
        measurement_names = set()
        
        for measurement_data in measurements:
            # Validate measurement data
            if 'name' not in measurement_data:
                raise serializers.ValidationError("Each measurement must have a 'name' field")
            
            name = measurement_data.get('name', '').strip().title()
            if not name:
                raise serializers.ValidationError("Measurement name cannot be empty")
            
            if name in measurement_names:
                raise serializers.ValidationError(f"Duplicate measurement name: {name}")
            measurement_names.add(name)
            
            # Validate measurement fields
            unit = measurement_data.get('unit', 'inches').strip()
            is_required = bool(measurement_data.get('is_required', False))
            is_active = bool(measurement_data.get('is_active', True))
            rank = int(measurement_data.get('rank', 0))
            
            validated_measurements.append({
                'name': name,
                'unit': unit,
                'is_required': is_required,
                'is_active': is_active,
                'rank': rank
            })
        
        return validated_measurements
    
    def create(self, validated_data):
        measurements_data = validated_data.pop('measurements', [])
        
        # Create size chart
        size_chart = SizeChart.objects.create(**validated_data)
        
        # Create measurements
        for measurement_data in measurements_data:
            SizeMeasurement.objects.create(
                size_chart=size_chart,
                **measurement_data
            )
        
        return size_chart
    
    def update(self, instance, validated_data):
        measurements_data = validated_data.pop('measurements', None)
        
        # Update size chart fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update measurements if provided
        if measurements_data is not None:
            # Clear existing measurements
            instance.measurements.all().delete()
            
            # Create new measurements
            for measurement_data in measurements_data:
                SizeMeasurement.objects.create(
                    size_chart=instance,
                    **measurement_data
                )
        
        return instance
    


# List/Detail Serializers (for GET operations)
class CustomFieldListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomField
        fields = [
            'id', 'name', 'label', 'field_type', 'placeholder', 'help_text',
            'default_value', 'options', 'is_required', 'min_length', 'max_length',
            'width_class', 'is_active', 'rank'
        ]


class CustomSectionListSerializer(serializers.ModelSerializer):
    fields = CustomFieldListSerializer(many=True, read_only=True)
    fields_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomSection
        fields = [
            'id', 'name', 'description', 'is_collapsed', 'is_active', 'rank',
            'fields', 'fields_count'
        ]
    
    def get_fields_count(self, obj):
        return obj.fields.filter(is_active=True).count()


class CustomTabListSerializer(serializers.ModelSerializer):
    category = CategoryListSerializer(read_only=True)
    sections = CustomSectionListSerializer(many=True, read_only=True)
    sections_count = serializers.SerializerMethodField()
    total_fields_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomTab
        fields = [
            'id', 'category', 'name', 'description', 'is_active', 'rank',
            'sections', 'sections_count', 'total_fields_count',
        ]
    
    def get_sections_count(self, obj):
        return obj.sections.filter(is_active=True).count()
    
    def get_total_fields_count(self, obj):
        return CustomField.objects.filter(
            section__tabs=obj,
            section__is_active=True,
            is_active=True
        ).count()


# Create/Update Serializers (for POST/PUT/PATCH operations)
class CustomFieldCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomField
        fields = [
            'section', 'name', 'label', 'field_type', 'placeholder', 'help_text',
            'default_value', 'options', 'is_required', 'min_length', 'max_length',
            'width_class', 'is_active', 'rank'
        ]
    
    def validate_options(self, value):
        """Validate options field"""
        if not value:
            return value
        
        if not isinstance(value, list):
            raise serializers.ValidationError("Options must be a list.")
        
        # Support both simple list ["Option1", "Option2"] and object list [{"label": "...", "value": "..."}]
        validated_options = []
        for option in value:
            if isinstance(option, str):
                validated_options.append(option.strip())
            elif isinstance(option, dict):
                if 'label' in option and 'value' in option:
                    validated_options.append({
                        'label': str(option['label']).strip(),
                        'value': str(option['value']).strip()
                    })
                else:
                    raise serializers.ValidationError("Option objects must have 'label' and 'value' keys.")
            else:
                raise serializers.ValidationError("Options must be strings or objects with 'label' and 'value'.")
        
        return validated_options


class CustomSectionCreateUpdateSerializer(serializers.ModelSerializer):
    fields = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of fields for this section"
    )
    
    class Meta:
        model = CustomSection
        fields = [
            'name', 'description', 'is_collapsed', 'is_active', 'rank', 'fields'
        ]
    
    def create(self, validated_data):
        fields_data = validated_data.pop('fields', [])
        
        # Create section
        section = CustomSection.objects.create(**validated_data)
        
        # Create fields
        for field_data in fields_data:
            CustomField.objects.create(section=section, **field_data)
        
        return section
    
    def update(self, instance, validated_data):
        fields_data = validated_data.pop('fields', None)
        
        # Update section attributes
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update fields if provided
        if fields_data is not None:
            # Clear existing fields
            instance.fields.all().delete()
            
            # Create new fields
            for field_data in fields_data:
                CustomField.objects.create(section=instance, **field_data)
        
        return instance


class CustomTabCreateUpdateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
        help_text="Single category ID (use this OR categories, not both)"
    )
    categories = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Category.objects.all()),
        write_only=True,
        required=False,
        allow_empty=False,
        help_text="List of category IDs - will create one CustomTab per category"
    )
    sections = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="List of section IDs to associate with this tab"
    )

    class Meta:
        model = CustomTab
        fields = ['category', 'categories', 'name', 'description', 'is_active', 'rank', 'sections']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make category not required since we have categories as alternative
        if 'category' in self.fields:
            self.fields['category'].required = False
            self.fields['category'].allow_null = True

    def to_internal_value(self, data):
        """Override to inject None for category if not provided but categories is"""
        # If categories is provided but not category, set category to None
        if 'categories' in data and 'category' not in data:
            data = data.copy() if hasattr(data, 'copy') else dict(data)
            data['category'] = None
        return super().to_internal_value(data)

    def validate(self, data):
        # Check that either category or categories is provided, not both
        has_category = 'category' in data and data.get('category') is not None
        has_categories = 'categories' in data and len(data.get('categories', [])) > 0

        if has_category and has_categories:
            raise serializers.ValidationError({
                'category': 'Provide either "category" or "categories", not both.'
            })

        if not has_category and not has_categories and not self.instance:
            raise serializers.ValidationError({
                'category': 'Either "category" or "categories" is required.'
            })

        return data

    def validate_sections(self, section_ids):
        """Validate that all section IDs exist"""
        if not section_ids:
            return section_ids

        # Check if all sections exist
        existing_sections = CustomSection.objects.filter(id__in=section_ids)
        existing_ids = set(existing_sections.values_list('id', flat=True))
        provided_ids = set(section_ids)

        missing_ids = provided_ids - existing_ids
        if missing_ids:
            raise serializers.ValidationError(
                f"Section IDs do not exist: {list(missing_ids)}"
            )

        return section_ids

    def create(self, validated_data):
        section_ids = validated_data.pop('sections', [])
        categories_data = validated_data.pop('categories', None)

        # If categories list is provided, create multiple CustomTab records
        if categories_data:
            created_tabs = []
            for category in categories_data:
                tab = CustomTab.objects.create(
                    category=category,
                    name=validated_data.get('name'),
                    description=validated_data.get('description', ''),
                    is_active=validated_data.get('is_active', True),
                    rank=validated_data.get('rank', 0)
                )
                if section_ids:
                    tab.sections.set(CustomSection.objects.filter(id__in=section_ids))
                created_tabs.append(tab)

            # Store all created instances for custom response handling
            self.context['created_tabs'] = created_tabs
            return created_tabs[0] if created_tabs else None
        else:
            # Single category - original behavior
            tab = CustomTab.objects.create(**validated_data)
            if section_ids:
                tab.sections.set(CustomSection.objects.filter(id__in=section_ids))
            return tab

    def update(self, instance, validated_data):
        section_ids = validated_data.pop('sections', None)
        validated_data.pop('categories', None)  # Remove categories from update

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if section_ids is not None:
            instance.sections.set(CustomSection.objects.filter(id__in=section_ids))
        return instance