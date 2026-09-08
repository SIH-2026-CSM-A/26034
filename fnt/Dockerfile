# PCCS officer surface: build the static bundle, serve it with nginx.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Vite freezes this into the bundle at build time. Changing the backend URL means
# rebuilding this image, not restarting the container.
# Defaults to the same-origin path nginx proxies. An absolute URL here reintroduces
# the cross-origin request this image exists to avoid.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.29-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Serves the bundle and proxies /api to the backend, so the two share one origin and
# there is no CORS to configure. See fnt/nginx.conf.
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
