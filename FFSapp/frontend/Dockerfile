# Use an official Nginx image as the base
FROM nginx:alpine

# Copy the custom Nginx configuration file into the container
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy your frontend static files into Nginx's default public directory
COPY . /usr/share/nginx/html

# Expose port 80, which Nginx serves on by default
EXPOSE 80

# Command to run Nginx when the container starts
CMD ["nginx", "-g", "daemon off;"]
