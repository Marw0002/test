from django import forms
from django.core import exceptions
from django.utils.translation import ugettext_lazy as _
from treebeard.forms import movenodeform_factory

from oscar.core.loading import get_class, get_model
from oscar.core.utils import slugify
from oscar.forms.widgets import DateTimePickerInput, ImageInput

Product = get_model('catalogue', 'Product')
Category = get_model('catalogue', 'Category')
Company = get_model ('customer','Company')
Theme = get_model('catalogue','ProjectTheme')
Color = get_model('catalogue','ProjectColor')
ProductCategory = get_model('catalogue', 'ProductCategory')
ProductImage = get_model('catalogue', 'ProductImage')
ProductRecommendation = get_model('catalogue', 'ProductRecommendation')
ProductSelect = get_class('dashboard.catalogue.widgets', 'ProductSelect')


CategoryForm = movenodeform_factory(
    Category,
    fields=['name', 'description'])


class ProductSearchForm(forms.Form):
    title = forms.CharField(
        max_length=255, required=False, label=_('Idea title'))

    def clean(self):
        cleaned_data = super(ProductSearchForm, self).clean()
        cleaned_data['title'] = cleaned_data['title'].strip()
        return cleaned_data


def _attr_text_field(attribute):
    return forms.CharField(label=attribute.name,
                           required=attribute.required)


def _attr_textarea_field(attribute):
    return forms.CharField(label=attribute.name,
                           widget=forms.Textarea(),
                           required=attribute.required)


def _attr_integer_field(attribute):
    return forms.IntegerField(label=attribute.name,
                              required=attribute.required)


def _attr_boolean_field(attribute):
    return forms.BooleanField(label=attribute.name,
                              required=attribute.required)


def _attr_float_field(attribute):
    return forms.FloatField(label=attribute.name,
                            required=attribute.required)


def _attr_date_field(attribute):
    return forms.DateField(label=attribute.name,
                           required=attribute.required,
                           widget=forms.widgets.DateInput)


def _attr_datetime_field(attribute):
    return forms.DateTimeField(label=attribute.name,
                               required=attribute.required,
                               widget=DateTimePickerInput())


def _attr_option_field(attribute):
    return forms.ModelChoiceField(
        label=attribute.name,
        required=attribute.required,
        queryset=attribute.option_group.options.all())


def _attr_multi_option_field(attribute):
    return forms.ModelMultipleChoiceField(
        label=attribute.name,
        required=attribute.required,
        queryset=attribute.option_group.options.all())


def _attr_entity_field(attribute):
    # Product entities don't have out-of-the-box supported in the ProductForm.
    # There is no ModelChoiceField for generic foreign keys, and there's no
    # good default behaviour anyway; offering a choice of *all* model instances
    # is hardly useful.
    return None


def _attr_numeric_field(attribute):
    return forms.FloatField(label=attribute.name,
                            required=attribute.required)


def _attr_file_field(attribute):
    return forms.FileField(
        label=attribute.name, required=attribute.required)


def _attr_image_field(attribute):
    return forms.ImageField(
        label=attribute.name, required=attribute.required)


class ProductForm(forms.ModelForm):
 
    class Meta:
        model = Product
        fields = [
            'title', 'description', 'theme','color','budget','company','color_name','theme_name','categories']		
        widgets = {
            'color_name': forms.HiddenInput(),
            'theme_name': forms.HiddenInput(),
        }			

    def __init__(self, user, company, data=None, parent=None, *args, **kwargs):
        self.set_initial(parent, kwargs)
        super(ProductForm, self).__init__(data, *args, **kwargs)
        self.fields["theme"] = forms.ModelMultipleChoiceField(queryset = Theme.objects.all())
        self.fields["color"] = forms.ModelMultipleChoiceField(queryset = Color.objects.all())
        self.fields["categories"] = forms.ModelChoiceField(queryset = Category.objects.all())
        self.user=user

        if 'title' in self.fields:
            self.fields['title'].widget = forms.TextInput(
                attrs={'autocomplete': 'off'})
        
        if not user.is_staff:
            self.fields['company'] = forms.ModelChoiceField (queryset=Company.objects.filter(id=company.id), initial=company, required = True)
            self.fields['company'].widget = forms.HiddenInput()
			
    def set_initial(self, parent, kwargs):
        """
        Set initial data for the form. Sets the correct product structure
        and fetches initial values for the dynamically constructed attribute
        fields.
        """

        if 'initial' not in kwargs:
            kwargs['initial'] = {}

    def clean_theme(self):
        """
        Checks for existing users with the supplied email address.
        """
        value = self.cleaned_data['theme']
        print(value)
        if len(value) > 2:
            raise forms.ValidationError("You can't select more than 2 items.")
        return value		

    def clean_color(self):
        """
        Checks for existing users with the supplied email address.
        """
        value = self.cleaned_data['color']
        if len(value) > 2:
            raise forms.ValidationError("You can't select more than 2 items.")
				
        return value		

    def clean_categories(self):
        """
        Checks for existing users with the supplied email address.
        """
        value = self.cleaned_data['categories']
        return value		
			


class ProductCategoryForm(forms.ModelForm):

    class Meta:
        model = ProductCategory
        fields = ('category', )


class ProductImageForm(forms.ModelForm):

    class Meta:
        model = ProductImage
        fields = ['product', 'original', 'caption']
        # use ImageInput widget to create HTML displaying the
        # actual uploaded image and providing the upload dialog
        # when clicking on the actual image.
        widgets = {
            'original': ImageInput(),
        }

    def save(self, *args, **kwargs):
        # We infer the display order of the image based on the order of the
        # image fields within the formset.
        kwargs['commit'] = False
        obj = super(ProductImageForm, self).save(*args, **kwargs)
        obj.display_order = self.get_display_order()
        obj.save()
        return obj

    def get_display_order(self):
        return self.prefix.split('-').pop()

    def clean_original(self):
        file = self.cleaned_data['original']
        if file:
            if file._size > 1*1024*1024:
                raise forms.ValidationError("Image file is too large ( > 1mb ).")
            return file
        else:
            raise forms.ValidationError("Could not read the uploaded file.")


class ProductRecommendationForm(forms.ModelForm):

    class Meta:
        model = ProductRecommendation
        fields = ['primary', 'recommendation', 'ranking']
        widgets = {
            'recommendation': ProductSelect,
        }

    def __init__(self, *args, **kwargs):
        super(ProductRecommendationForm, self).__init__(*args, **kwargs)
        self.fields['recommendation'].widget.attrs['class'] = "select2"
