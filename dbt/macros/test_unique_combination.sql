{# Test genérico: la combinación de columnas es única (equivalente a dbt_utils, sin paquetes). #}
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
