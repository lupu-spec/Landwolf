FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-fund
COPY web ./web
COPY scripts/build.mjs ./scripts/build.mjs
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 LANDWOLF_BIND_HOST=0.0.0.0
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY landwolf ./landwolf
COPY --from=frontend /build/landwolf/static ./landwolf/static
RUN useradd --system --uid 10001 --create-home landwolf
USER 10001
EXPOSE 8000
CMD ["python", "-m", "landwolf.serve"]
