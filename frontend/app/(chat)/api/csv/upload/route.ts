import { NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/app/(auth)/auth";

const CSVFileSchema = z.object({
  file: z
    .instanceof(Blob)
    .refine((file) => file.size <= 50 * 1024 * 1024, {
      message: "File size should be less than 50MB",
    })
    .refine(
      (file) =>
        file.type === "text/csv" ||
        file.type === "application/vnd.ms-excel" ||
        file.type === "application/csv",
      {
        message: "File type should be CSV",
      }
    ),
});

export async function POST(request: Request) {
  const session = await auth();

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (request.body === null) {
    return new Response("Request body is empty", { status: 400 });
  }

  try {
    const formData = await request.formData();
    const file = formData.get("csv") as Blob;

    if (!file) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
    }

    const validatedFile = CSVFileSchema.safeParse({ file });

    if (!validatedFile.success) {
      const errorMessage = validatedFile.error.errors
        .map((error) => error.message)
        .join(", ");

      return NextResponse.json({ error: errorMessage }, { status: 400 });
    }

    // Forward to backend ML service
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const backendFormData = new FormData();
    backendFormData.append("csv", file);

    try {
      const response = await fetch(`${backendUrl}/upload`, {
        method: "POST",
        body: backendFormData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        return NextResponse.json(
          { error: errorText || "Upload to backend failed" },
          { status: response.status }
        );
      }

      const data = await response.json();
      return NextResponse.json(data);
    } catch (error) {
      console.error("Backend upload error:", error);
      return NextResponse.json(
        { error: "Failed to upload to ML backend" },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error("Upload processing error:", error);
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    );
  }
}

