"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { PageShell } from "@/components/page-shell";
import {
  RequireAuth,
  useSession,
  type SessionUser,
} from "@/components/session";
import { Avatar } from "@/components/avatar";
import { PhotoPicker } from "@/components/photo-picker";
import {
  Alert,
  Button,
  Card,
  Field,
  Input,
  PageHeader,
  Textarea,
} from "@/components/ui";
import { apiRequest, type Schemas } from "@/lib/api-client";
import { uploadMedia } from "@/lib/uploads";

function EditProfile({ user }: { user: SessionUser }) {
  const { refresh } = useSession();
  const [name, setName] = useState(user.display_name);
  const [bio, setBio] = useState(user.bio ?? "");
  const [photos, setPhotos] = useState<File[]>([]);
  const [removeAvatar, setRemoveAvatar] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const avatar = photos[0]
        ? { avatar_key: await uploadMedia(photos[0], "avatar") }
        : removeAvatar
          ? { avatar_key: null }
          : {};
      const updated = await apiRequest<Schemas["CurrentUserResponse"]>(
        "/auth/me",
        {
          method: "PATCH",
          body: JSON.stringify({
            display_name: name.trim(),
            bio: bio.trim() || null,
            ...avatar,
          }),
        },
      );
      setName(updated.display_name);
      setBio(updated.bio ?? "");
      await refresh();
      setPhotos([]);
      setRemoveAvatar(false);
      setSaved(true);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Couldn't save your profile.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Link className="text-sm font-bold text-muted" href="/profile">
        ← Your profile
      </Link>
      <PageHeader
        title="Edit profile"
        description="Choose how you appear to people you rent with."
      />
      <form onSubmit={submit}>
        <Card className="space-y-5">
          <div className="flex items-center gap-4">
            <Avatar
              name={name || user.display_name}
              url={removeAvatar ? null : user.avatar_url}
              large={true}
            />
            {user.avatar_url && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setRemoveAvatar(!removeAvatar);
                  setSaved(false);
                }}
              >
                {removeAvatar ? "Keep current photo" : "Remove current photo"}
              </Button>
            )}
          </div>
          <Field label="Profile photo" hint="JPEG or PNG, up to 10 MB.">
            <PhotoPicker
              max={1}
              files={photos}
              onChange={(files) => {
                setPhotos(files);
                setSaved(false);
              }}
            />
          </Field>
          <Field label="Display name">
            <Input
              required
              maxLength={80}
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                setSaved(false);
              }}
            />
          </Field>
          <Field label="About you" hint={`${bio.length}/500 characters`}>
            <Textarea
              maxLength={500}
              value={bio}
              onChange={(event) => {
                setBio(event.target.value);
                setSaved(false);
              }}
            />
          </Field>
          <Field label="Email" hint="Account email is read-only in this demo.">
            <Input type="email" value={user.email} readOnly />
          </Field>
          {error && <Alert>{error}</Alert>}
          {saved && <Alert tone="success">Profile saved.</Alert>}
          <Button type="submit" busy={busy} disabled={!name.trim()}>
            Save profile
          </Button>
        </Card>
      </form>
    </>
  );
}

export default function EditProfilePage() {
  return (
    <PageShell width="max-w-2xl">
      <RequireAuth>{(user) => <EditProfile user={user} />}</RequireAuth>
    </PageShell>
  );
}
