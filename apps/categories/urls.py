from django.urls import path
from apps.categories.views import CategoryListCreateView, CategoryTreeView

urlpatterns = [
    path('', CategoryListCreateView.as_view(), name='category_list_create'),
    path('tree/', CategoryTreeView.as_view(), name='category_tree'),
]
