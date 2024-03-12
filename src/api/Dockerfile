# Base Image Dockerfile
FROM python:3.11-slim AS base

WORKDIR /base

COPY api-base-requirements.txt ./
RUN pip install --no-cache-dir -r api-base-requirements.txt