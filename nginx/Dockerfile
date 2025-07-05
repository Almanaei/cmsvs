FROM nginx:1.25-alpine

# Install additional packages for better functionality
RUN apk add --no-cache \
    curl \
    tzdata \
    && rm -rf /var/cache/apk/*

# Set timezone
ENV TZ=UTC

# Create nginx user and directories
RUN addgroup -g 101 -S nginx || true \
    && adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx || true

# Remove default nginx configurations
RUN rm -f /etc/nginx/conf.d/default.conf \
    && rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true \
    && rm -f /etc/nginx/sites-available/default 2>/dev/null || true

# Create necessary directories
RUN mkdir -p /var/log/nginx /var/cache/nginx /etc/nginx/ssl \
    && chown -R nginx:nginx /var/log/nginx /var/cache/nginx \
    && chmod -R 755 /var/log/nginx /var/cache/nginx

# Copy our custom configuration
COPY --chown=nginx:nginx nginx.conf /etc/nginx/nginx.conf
COPY --chown=nginx:nginx conf.d/app.conf /etc/nginx/conf.d/app.conf

# Note: nginx -t test is skipped during build as upstream services are not available

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expose ports
EXPOSE 80 443

# Use tini for proper signal handling
RUN apk add --no-cache tini
ENTRYPOINT ["tini", "--"]

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
