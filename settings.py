# Django settings for the example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
ROOT_URLCONF = 'urls'

DEFAULT_LANG = 'zh-cn'

PAGE_CACHE_DISABLED = True

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates".
    # Always use forward slashes, even on Windows.
    './templates',
)

INSTALLED_APPS = (
    'cc_addons',
)

def main():
    pass

if __name__ == '__main__':
  main()
  
