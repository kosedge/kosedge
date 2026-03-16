// apps/web/app/api/auth/register/route.ts
import crypto from "node:crypto";
import { prisma } from "@/lib/db";
import { jsonError, jsonOk } from "@/lib/api/response";
import { handleApiError } from "@/lib/api/error-handler";
import { logError } from "@/lib/logger";
import { hash } from "bcryptjs";
import { z } from "zod";

function getRequestId(req: Request): string {
  return req.headers.get("x-request-id") ?? req.headers.get("x-correlation-id") ?? crypto.randomUUID();
}

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().min(1).optional(),
});

export async function POST(req: Request) {
  const requestId = getRequestId(req);
  try {
    const body = await req.json();
    const parsed = registerSchema.safeParse(body);

    if (!parsed.success) {
      return jsonError(400, "Invalid input", { code: "VALIDATION_ERROR" });
    }

    const { email, password, name } = parsed.data;

    const existingUser = await prisma.user.findUnique({
      where: { email },
    });

    if (existingUser) {
      return jsonError(409, "User already exists");
    }

    const hashedPassword = await hash(password, 12);

    const user = await prisma.user.create({
      data: {
        email,
        password: hashedPassword,
        name: name ?? null,
      },
      select: {
        id: true,
        email: true,
        name: true,
        role: true,
      },
    });

    const res = jsonOk({ message: "User created successfully", user }, { status: 201 });
    res.headers.set("x-request-id", requestId);
    return res;
  } catch (error) {
    logError(error instanceof Error ? error : new Error(String(error)), { route: "auth/register" });
    const errRes = handleApiError(error);
    errRes.headers.set("x-request-id", requestId);
    return errRes;
  }
}
