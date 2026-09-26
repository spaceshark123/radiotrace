FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY
ARG VITE_GOOGLE_MAP_ID=$VITE_GOOGLE_MAP_ID
ARG VITE_API_BASE=/api
ENV VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY
ENV VITE_GOOGLE_MAP_ID=$VITE_GOOGLE_MAP_ID
ENV VITE_API_BASE=$VITE_API_BASE

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
