# Web Service Dockerfile for serving static files

FROM nginx:alpine

# Copy nginx configuration
COPY docker/web/nginx.conf /etc/nginx/nginx.conf

# Copy static HTML files
COPY src/mod_ui_original/html/ /usr/share/nginx/html/

# Create logs directory
RUN mkdir -p /var/log/nginx

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1