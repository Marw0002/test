from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, View

from oscar.apps.customer.reviews.signals import review_added
from oscar.core.loading import get_classes, get_model
from oscar.core.utils import redirect_to_referrer

VendorReviewForm, VoteForm, SortReviewsForm = get_classes(
    'customer.reviews.forms',
    ['VendorReviewForm', 'VoteForm', 'SortReviewsForm'])
Vote = get_model('reviews', 'vote')
VendorReview = get_model('reviews', 'VendorReview')
Company = get_model('customer', 'company')


class CreateVendorReview(CreateView):
    template_name = "customer/reviews/review_form.html"
    model = VendorReview
    product_model = Company
    form_class = VendorReviewForm
    view_signal = review_added

    def dispatch(self, request, *args, **kwargs):
        self.company = get_object_or_404(
            self.product_model, pk=kwargs['company_pk'])
        # check permission to leave review
        if not self.company.is_review_permitted(request.user):
            if self.company.has_review_by(request.user):
                message = _("You have already reviewed this product!")
            else:
                message = _("You can't leave a review for this product.")
            messages.warning(self.request, message)
            return redirect(self.company.get_absolute_url())

        return super(CreateVendorReview, self).dispatch(
            request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CreateVendorReview, self).get_context_data(**kwargs)
        context['company'] = self.company
        return context

    def get_form_kwargs(self):
        kwargs = super(CreateVendorReview, self).get_form_kwargs()
        kwargs['company'] = self.company
        kwargs['user'] = self.request.user
        return kwargs
		

    def form_valid(self, form):
        response = super(CreateVendorReview, self).form_valid(form)
        self.send_signal(self.request, response, self.object)
        return response

    def get_success_url(self):
        messages.success(
            self.request, _("Thank you for reviewing this product"))
        return self.company.get_absolute_url()

    def send_signal(self, request, response, review):
        self.view_signal.send(sender=self, review=review, user=request.user,
                              request=request, response=response)


class VendorReviewDetail(DetailView):
    template_name = "customer/reviews/review_detail.html"
    context_object_name = 'review'
    model = VendorReview

    def get_context_data(self, **kwargs):
        context = super(VendorReviewDetail, self).get_context_data(**kwargs)
        context['company'] = get_object_or_404(
            Company, pk=self.kwargs['company_pk'])
        return context


class AddVoteView(View):
    """
    Simple view for voting on a review.

    We use the URL path to determine the product and review and use a 'delta'
    POST variable to indicate it the vote is up or down.
    """

    def post(self, request, *args, **kwargs):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'])
        review = get_object_or_404(VendorReview, pk=self.kwargs['pk'])

        form = VoteForm(review, request.user, request.POST)
        if form.is_valid():
            if form.is_up_vote:
                review.vote_up(request.user)
            elif form.is_down_vote:
                review.vote_down(request.user)
            messages.success(request, _("Thanks for voting!"))
        else:
            for error_list in form.errors.values():
                for msg in error_list:
                    messages.error(request, msg)
        return redirect_to_referrer(request, company.get_absolute_url())


class VendorReviewList(ListView):
    """
    Browse reviews for a product
    """
    template_name = 'customer/reviews/review_list.html'
    context_object_name = "reviews"
    model = VendorReview
    company_model = Company
    paginate_by = settings.OSCAR_REVIEWS_PER_PAGE

    def get_queryset(self):
        qs = self.model.objects.approved().filter(company=self.kwargs['company_pk'])
        self.form = SortReviewsForm(self.request.GET)
        if self.form.is_valid():
            sort_by = self.form.cleaned_data['sort_by']
            if sort_by == SortReviewsForm.SORT_BY_RECENCY:
                return qs.order_by('-date_created')
        return qs.order_by('-score')

    def get_context_data(self, **kwargs):
        context = super(VendorReviewList, self).get_context_data(**kwargs)
        context['company'] = get_object_or_404(
            self.company_model, pk=self.kwargs['company_pk'])
        context['form'] = self.form
        return context
