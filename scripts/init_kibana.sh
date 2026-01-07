#!/bin/bash
# Script to initialize Kibana dashboards

# Wait for Kibana to be ready
echo "Waiting for Kibana to be ready..."
until curl -s http://localhost:5601/api/status | grep -q '"level":"available"'; do
    sleep 5
    echo "Waiting for Kibana..."
done
echo "Kibana is ready!"

# Create index patterns
echo "Creating index patterns..."

# Create recommendation-logs index pattern
curl -X POST "http://localhost:5601/api/saved_objects/index-pattern/recommendation-logs-*" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d '{
        "attributes": {
            "title": "recommendation-logs-*",
            "timeFieldName": "@timestamp"
        }
    }'

# Create recommendation-api index pattern
curl -X POST "http://localhost:5601/api/saved_objects/index-pattern/recommendation-api-*" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d '{
        "attributes": {
            "title": "recommendation-api-*",
            "timeFieldName": "@timestamp"
        }
    }'

# Create recommendation-errors index pattern
curl -X POST "http://localhost:5601/api/saved_objects/index-pattern/recommendation-errors-*" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d '{
        "attributes": {
            "title": "recommendation-errors-*",
            "timeFieldName": "@timestamp"
        }
    }'

# Import dashboards
echo "Importing dashboards..."
if [ -f "./monitoring/kibana/dashboards/recommendation-dashboards.ndjson" ]; then
    curl -X POST "http://localhost:5601/api/saved_objects/_import" \
        -H "kbn-xsrf: true" \
        --form file=@./monitoring/kibana/dashboards/recommendation-dashboards.ndjson
    echo "Dashboards imported successfully!"
else
    echo "Dashboard file not found!"
fi

echo "Kibana initialization complete!"
echo ""
echo "Access points:"
echo "  - Kibana: http://localhost:5601"
echo "  - APM:    http://localhost:5601/app/apm"
echo "  - Logs:   http://localhost:5601/app/discover"
