# KaushalPath frontend — build with Node, serve with nginx.
#
# VITE_API_BASE is a BUILD-time value (Vite inlines it into the bundle), not a
# runtime env. For the production stack we build with `/api` and let Nginx
# reverse-proxy /api -> backend, so the browser talks to a single origin
# (no client-side CORS at all). Default keeps local dev/proxy working.
FROM node:20-alpine AS build
WORKDIR /app

ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=${VITE_API_BASE}

COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

FROM nginx:alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
