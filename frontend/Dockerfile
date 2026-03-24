FROM node:20-alpine

WORKDIR /app

# Install dependencies only — source is mounted at runtime
COPY package.json package-lock.json ./
RUN npm ci

CMD ["npm", "run", "dev"]
