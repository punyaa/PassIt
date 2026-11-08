"use client";
import type { Schemas } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";
import { Alert, Button, Card, EmptyState, Spinner } from "./ui";

export function ProfileReviews({ userId }: { userId: string }) {
  const reviews = useApi<Schemas["Review"][]>(
    `/reviews?user_id=${userId}&limit=20`,
  );
  return (
    <section className="mt-9">
      <h2 className="mb-5 text-2xl font-bold">Received reviews</h2>
      {reviews.loading && <Spinner label="Loading reviews…" />}
      {reviews.error && (
        <Alert>
          {reviews.error.message}{" "}
          <Button onClick={reviews.reload} variant="secondary">
            Try again
          </Button>
        </Alert>
      )}
      {reviews.data?.length === 0 && (
        <EmptyState title="No reviews yet">
          Reviews from rental partners will appear here.
        </EmptyState>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        {reviews.data?.map((review) => (
          <Card key={review.id}>
            <p
              className="font-bold"
              aria-label={`${review.rating} out of 5 stars`}
            >
              {"★".repeat(review.rating)}
            </p>
            {review.comment && (
              <p className="mt-3 leading-6">{review.comment}</p>
            )}
            <p className="mt-3 text-sm text-muted">
              {review.author_display_name}
            </p>
          </Card>
        ))}
      </div>
    </section>
  );
}
