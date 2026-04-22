export function getErrorInfo(error) {
  const raw = typeof error === "string" ? error : (error?.message || "");
  const lower = raw.toLowerCase();

  if (!raw || lower === "failed to fetch" || lower.includes("networkerror") || lower.includes("network request failed") || lower.includes("load failed")) {
    return {
      message: "Couldn't reach the server.",
      explanation: "Check your connection and try again.",
    };
  }
  if (lower.includes("401") || lower.includes("unauthorized") || lower.includes("not authenticated") || lower.includes("session expired") || lower.includes("invalid token")) {
    return {
      message: "Your session has expired.",
      explanation: "Please sign in again.",
    };
  }
  if (lower.includes("429") || lower.includes("rate limit") || lower.includes("too many requests")) {
    return {
      message: "Hit a rate limit.",
      explanation: "Wait a moment and try again.",
    };
  }
  if (lower.includes("500") || lower.includes("502") || lower.includes("503") || lower.includes("server error") || lower.includes("internal error") || lower.includes("bad gateway")) {
    return {
      message: "Server encountered an error.",
      explanation: "This usually resolves in a few seconds. Try again.",
    };
  }
  if (lower.includes("claude") || lower.includes("anthropic") || lower.includes("overloaded") || (lower.includes("generat") && lower.includes("fail"))) {
    return {
      message: "AI service temporarily unavailable.",
      explanation: "The style analysis service is taking longer than expected. Try again.",
    };
  }
  if (lower.includes("timeout") || lower.includes("timed out") || lower.includes("took too long") || lower.includes("etimedout")) {
    return {
      message: "Request took too long.",
      explanation: "Try again — the AI services occasionally take more time.",
    };
  }
  if (lower.includes("too large") || lower.includes("10mb") || lower.includes("10 mb") || lower.includes("file size") || lower.includes("size limit") || lower.includes("payload too large")) {
    return {
      message: "Image too large.",
      explanation: "Please use a photo under 10MB.",
    };
  }

  return {
    message: raw || "Something went wrong.",
    explanation: "Please try again or report this if it keeps happening.",
  };
}
