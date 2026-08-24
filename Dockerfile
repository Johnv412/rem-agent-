# RemAgent Dream Engine dashboard — single Cloud Run service serving the
# built SPA (dist/) statically plus the /api Express backend (dist/server.cjs).
# Deploy with: gcloud run deploy --source . (see scripts/deploy-cloudrun.sh)

FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-slim
ENV NODE_ENV=production
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist
# The Python framework sources served by GET /api/files/source (the in-app
# code viewer reads them from process.cwd()).
COPY remagent ./remagent
COPY tests ./tests
COPY pyproject.toml README.md ./
# Cloud Run injects PORT; server.cjs listens on it (defaults to 3000 locally).
EXPOSE 8080
CMD ["node", "dist/server.cjs"]
