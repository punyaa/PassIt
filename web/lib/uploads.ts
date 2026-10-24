import { ApiError, apiPost, type Schemas } from "./api-client";

export type MediaStage = Schemas["PresignRequest"]["stage"];
export type UploadType = Schemas["PresignRequest"]["content_type"];

export const ACCEPTED_TYPES: UploadType[] = ["image/jpeg", "image/png"];
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

/** Upload one file straight to storage with a signed URL; returns the media key. */
export async function uploadMedia(file: File, stage: MediaStage): Promise<string> {
  if (!ACCEPTED_TYPES.includes(file.type as UploadType)) {
    throw new ApiError(400, `${file.name}: use a JPEG or PNG photo.`);
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new ApiError(400, `${file.name} is larger than 10 MB.`);
  }
  const presign = await apiPost<Schemas["PresignResponse"]>("/media/presign", {
    stage,
    content_type: file.type,
  });
  let response: Response;
  try {
    response = await fetch(presign.upload_url, { method: "PUT", body: file, headers: presign.headers });
  } catch {
    throw new ApiError(0, `Upload of ${file.name} failed. Check your connection and try again.`);
  }
  if (!response.ok) throw new ApiError(response.status, `Upload of ${file.name} failed (${response.status}).`);
  return presign.key;
}
