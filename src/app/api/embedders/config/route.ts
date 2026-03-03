import { NextResponse } from 'next/server';

const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

export async function GET() {
  try {
    const targetUrl = `${TARGET_SERVER_BASE_URL}/embedders/config`;

    const backendResponse = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      cache: 'no-store',
    });

    if (!backendResponse.ok) {
      return NextResponse.json(
        { error: `Backend service responded with status: ${backendResponse.status}` },
        { status: backendResponse.status }
      );
    }

    const embedderConfig = await backendResponse.json();
    return NextResponse.json(embedderConfig);
  } catch (error) {
    console.error('Error fetching embedder configurations:', error);
    return new NextResponse(JSON.stringify({ error: String(error) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
