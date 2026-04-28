{% macro match_keywords(column_name, keywords_list) %}
    (
        {% for keyword in keywords_list %}
            {{ column_name }} ILIKE '%{{ keyword }}%'
            {% if not loop.last %} OR {% endif %}
        {% endfor %}
    )
{% endmacro %}