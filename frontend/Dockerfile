FROM node:18-slim

WORKDIR /app

# Install dependencies if package.json exists
# In docker-compose we also mount the node_modules
# but this ensures a clean start
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

# Run dev server
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
