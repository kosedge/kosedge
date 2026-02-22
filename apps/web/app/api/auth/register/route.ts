// apps/web/app/api/auth/register/route.ts
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { hash } from "bcryptjs";
import { z } from "zod";
import { withErrorHandler, ApiError } from "@/lib/api/error-handler";

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().min(1).optional(),
});

async function registerHandler(req: Request): Promise<NextResponse> {
  const body = await req.json();
  const parsed = registerSchema.safeParse(body);

  if (!parsed.success) {
    throw new ApiError(
      400,
      "Invalid input",
      "VALIDATION_ERROR",
      parsed.error.issues,
    );
  }

  const { email, password, name } = parsed.data;

  const existingUser = await prisma.user.findUnique({
    where: { email },
  });

  if (existingUser) {
    throw new ApiError(409, "User already exists", "CONFLICT");
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

  return NextResponse.json(
    { message: "User created successfully", user },
    { status: 201 },
  );
}

export const POST = withErrorHandler(registerHandler);
