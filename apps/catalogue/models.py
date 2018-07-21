"""
Vanilla product models
"""
from oscar.apps.catalogue.abstract_models import *  # noqa
from oscar.core.loading import is_model_registered

__all__ = ['ProductAttributesContainer']


if not is_model_registered('catalogue', 'Category'):
    class Category(AbstractCategory):
        pass

    __all__.append('Category')


if not is_model_registered('catalogue', 'ProductCategory'):
    class ProductCategory(AbstractProductCategory):
        pass

    __all__.append('ProductCategory')


if not is_model_registered('catalogue', 'Product'):
    class Product(AbstractProduct):
        pass

    __all__.append('Product')


if not is_model_registered('catalogue', 'ProductRecommendation'):
    class ProductRecommendation(AbstractProductRecommendation):
        pass

    __all__.append('ProductRecommendation')


if not is_model_registered('catalogue', 'ProductImage'):
    class ProductImage(AbstractProductImage):
        pass

    __all__.append('ProductImage')

if not is_model_registered('catalogue', 'ProjectTheme'):
    class ProjectTheme(AbstractProjectTheme):
        pass

    __all__.append('ProjectTheme')
	
if not is_model_registered('catalogue', 'ProjectColor'):
    class ProjectColor(AbstractProjectColor):
        pass

    __all__.append('ProjectColor')
		