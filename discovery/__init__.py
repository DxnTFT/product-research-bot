# Primary discovery method - uses real Google Trends data
from .trends_to_products_finder import TrendsToProductsFinder

# Alternative finders (use Google Trends related queries)
from .niche_finder import NicheFinder
from .simple_niche_finder import SimpleNicheFinder

# DEPRECATED - These use hardcoded product lists, not recommended
# from .amazon_direct_finder import AmazonDirectFinder
# from .curated_products_finder import CuratedProductsFinder
