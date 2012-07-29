import simplejson

from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
def load_chart(hco):
    embed_script = '<script type="text/javascript">\nvar _chartchemy_hco = %s;\n</script>\n' % hco
    return mark_safe(embed_script)
