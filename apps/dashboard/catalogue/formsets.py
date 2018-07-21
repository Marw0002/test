from django import forms
from django.core import exceptions
from django.forms.models import inlineformset_factory
from django.utils.translation import ugettext_lazy as _

from oscar.core.loading import get_classes, get_model

Product = get_model('catalogue', 'Product')
Category = get_model('catalogue', 'Category')
ProductCategory = get_model('catalogue', 'ProductCategory')
ProductImage = get_model('catalogue', 'ProductImage')

(ProductCategoryForm,
 ProductImageForm) = \
    get_classes('dashboard.catalogue.forms',
                ('ProductCategoryForm',
                 'ProductImageForm'))

BaseProductCategoryFormSet = inlineformset_factory(
    Product, ProductCategory, form=ProductCategoryForm, extra=1,
    can_delete=True)
	

class ProductCategoryFormSet(BaseProductCategoryFormSet):

    def __init__(self, user, *args, **kwargs):
        # This function just exists to drop the extra arguments
        super(ProductCategoryFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        if self.get_num_categories()==0:
            raise forms.ValidationError(
                _("Please choose category"))
				
    def get_num_categories(self):
        num_categories = 0
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if (hasattr(form, 'cleaned_data')
                    and form.cleaned_data.get('category', None)
                    and not form.cleaned_data.get('DELETE', False)):
                num_categories += 1
        return num_categories

BaseProductImageFormSet = inlineformset_factory(
    Product, ProductImage, form=ProductImageForm, extra=4)

class ProductImageFormSet(BaseProductImageFormSet):

    def __init__(self, user, *args, **kwargs):
        super(ProductImageFormSet, self).__init__(*args, **kwargs)