from oscar.core.loading import get_class

SearchForm = get_class('search.forms', 'SearchForm')
SearchForm2 = get_class('search.forms', 'SearchForm2')

def search_form(request):
    """
    Ensure that the search form is available site wide
    """
    return {'search_form': SearchForm(request.GET)}
	
	
def search_form2(request):
    """
    Ensure that the search form is available site wide
    """
    return {'search_form2': SearchForm2(request.GET)}	
