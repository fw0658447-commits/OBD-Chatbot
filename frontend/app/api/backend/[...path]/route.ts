import { NextRequest, NextResponse } from 'next/server';

const INTERNAL_BACKEND_URL = process.env.INTERNAL_BACKEND_URL || 'http://backend:8000';

type RouteContext = {
  params: Promise<{ path?: string[] }>;
};

async function proxy(request: NextRequest, context: RouteContext) {
  const params = await context.params;
  const path = (params.path ?? []).join('/');
  const incomingUrl = new URL(request.url);
  const targetUrl = `${INTERNAL_BACKEND_URL}/${path}${incomingUrl.search}`;

  const headers = new Headers(request.headers);
  headers.delete('host');
  headers.delete('connection');
  headers.delete('content-length');

  try {
    const method = request.method.toUpperCase();
    const hasBody = !['GET', 'HEAD'].includes(method);
    const response = await fetch(targetUrl, {
      method,
      headers,
      body: hasBody ? await request.text() : undefined,
      cache: 'no-store'
    });

    const responseHeaders = new Headers(response.headers);
    responseHeaders.set('x-trading-cockpit-proxy', 'frontend-next-proxy');

    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    });
  } catch (error) {
    return NextResponse.json(
      {
        status: 'error',
        detail: error instanceof Error ? error.message : String(error),
        target_url: targetUrl,
        hint: 'Frontend proxy konnte Backend nicht erreichen. Pruefe docker compose ps und backend logs.'
      },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
