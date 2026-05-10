import { AccessToken } from "livekit-server-sdk";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type TokenRequest = {
  identity: string;
  name: string;
  room: string;
  metadata?: Record<string, string>;
  canPublish?: boolean;
  canSubscribe?: boolean;
};

export async function POST(request: Request) {
  try {
    const apiKey = process.env.LIVEKIT_API_KEY;
    const apiSecret = process.env.LIVEKIT_API_SECRET;

    if (!apiKey || !apiSecret) {
      return NextResponse.json(
        {
          error: "LiveKit credentials are missing.",
          hasKey: Boolean(apiKey),
          hasSecret: Boolean(apiSecret)
        },
        { status: 500 }
      );
    }

    const body = (await request.json()) as TokenRequest;
    const token = new AccessToken(apiKey, apiSecret, {
      identity: body.identity,
      name: body.name,
      metadata: body.metadata ? JSON.stringify(body.metadata) : undefined
    });

    const canPublish = body.canPublish ?? false;
    const canSubscribe = body.canSubscribe ?? true;

    token.addGrant({
      room: body.room,
      roomJoin: true,
      canPublish,
      canSubscribe
    });

    const jwt = await token.toJwt();
    const tokenString =
      typeof jwt === "string" ? jwt : Buffer.from(jwt).toString("utf-8");

    return NextResponse.json({ token: tokenString });
  } catch (err) {
    return NextResponse.json(
      {
        error: err instanceof Error ? err.message : "Token generation failed."
      },
      { status: 500 }
    );
  }
}
