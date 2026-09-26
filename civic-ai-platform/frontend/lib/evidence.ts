export function evidenceConfidenceClass(percentage: number): string {
  if (percentage >= 75) return "bg-emerald-500";
  if (percentage >= 40) return "bg-amber-500";
  return "bg-red-500";
}

export function evidenceConfidenceLabel(percentage: number): string {
  if (percentage >= 75) return "High evidence confidence";
  if (percentage >= 40) return "Moderate evidence confidence";
  return "Low evidence confidence";
}

export function formatEvidenceAge(ageHours: number | null | undefined): string {
  if (ageHours === null || ageHours === undefined || !Number.isFinite(ageHours)) {
    return "Evidence timestamp unavailable";
  }
  if (ageHours < 1) return "Evidence updated less than 1 hour ago";
  if (ageHours < 24) {
    const hours = Math.round(ageHours * 10) / 10;
    return `Evidence updated ${hours} ${hours === 1 ? "hour" : "hours"} ago`;
  }

  const days = Math.round((ageHours / 24) * 10) / 10;
  return `Evidence updated ${days} ${days === 1 ? "day" : "days"} ago`;
}

export function formatUploadedTimestamp(
  uploadedAt?: string | null,
  ageHours?: number | null,
): string | null {
  if (ageHours !== null && ageHours !== undefined && ageHours < 24) {
    return formatEvidenceAge(ageHours).replace("Evidence updated", "Uploaded");
  }

  if (uploadedAt) {
    const date = new Date(uploadedAt);
    if (!Number.isNaN(date.getTime())) {
      return `Uploaded on ${date.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })}`;
    }
  }

  if (ageHours !== null && ageHours !== undefined) {
    const days = Math.round((ageHours / 24) * 10) / 10;
    return `Uploaded ${days} ${days === 1 ? "day" : "days"} ago`;
  }
  return null;
}
