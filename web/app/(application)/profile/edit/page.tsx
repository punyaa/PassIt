"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ConfirmAction } from "@/components/confirm-action";
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
  Spinner,
  Textarea,
} from "@/components/ui";
import { apiRequest, type Schemas } from "@/lib/api-client";
import { uploadMedia } from "@/lib/uploads";
import { useApi } from "@/lib/use-api";

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
      <DeleteAccount />
    </>
  );
}

function plural(count: number, word: string) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

/** Erases the person; keeps other people's bookings, payments and reviews intact. */
function DeleteAccount() {
  const router = useRouter();
  const { refresh } = useSession();
  const preview = useApi<Schemas["AccountDeletionPreview"]>("/auth/me/deletion");
  const [password, setPassword] = useState("");

  async function remove() {
    await apiRequest<void>("/auth/me/delete", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    router.replace("/login?deleted=1");
    await refresh();
  }

  const data = preview.data;
  return (
    <section className="mt-6">
      <Card className="space-y-4">
        <h2 className="text-xl font-bold">Delete account</h2>
        {preview.loading && <Spinner label="Checking your account…" />}
        {preview.error && (
          <Alert>
            Couldn&apos;t check your account.{" "}
            <Button onClick={preview.reload} variant="secondary">
              Try again
            </Button>
          </Alert>
        )}
        {data && !data.allowed && (
          <p className="text-sm leading-6 text-muted">
            You have {plural(data.open_rentals, "rental")} in progress. Finish
            or cancel {data.open_rentals === 1 ? "it" : "them"} before
            deleting your account, so nobody&apos;s fee or deposit is left
            mid-rental.
          </p>
        )}
        {data && data.allowed && (
          <>
            <div className="space-y-2 text-sm leading-6 text-muted">
              <p>
                Deleting your account permanently erases your name, email,
                password, bio and profile photo. You won&apos;t be able to sign
                in again, though you can sign up later with the same email.
              </p>
              <ul className="list-disc pl-5">
                {data.listings_deleted > 0 && (
                  <li>
                    {plural(data.listings_deleted, "listing")} never rented
                    will be deleted.
                  </li>
                )}
                {data.listings_archived > 0 && (
                  <li>
                    {plural(data.listings_archived, "listing")} with past
                    rentals will be hidden and stripped of photos and
                    description.
                  </li>
                )}
                <li>
                  Past rentals, payments and reviews stay for the other person,
                  shown as &ldquo;Deleted user&rdquo;.
                </li>
              </ul>
            </div>
            <Field label="Confirm with your password">
              <Input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            <ConfirmAction
              title="Delete your account permanently?"
              description="This can't be undone."
              trigger="Delete account"
              confirmLabel="Delete my account"
              variant="danger"
              onConfirm={remove}
              disabled={!password}
            />
          </>
        )}
      </Card>
    </section>
  );
}

export default function EditProfilePage() {
  return (
    <PageShell width="max-w-2xl">
      <RequireAuth>{(user) => <EditProfile user={user} />}</RequireAuth>
    </PageShell>
  );
}
