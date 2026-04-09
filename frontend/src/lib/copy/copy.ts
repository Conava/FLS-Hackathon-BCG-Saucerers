/**
 * Centralized copy module — all user-facing static strings live here.
 *
 * Wellness framing rules (see docs/08-legal-compliance.md):
 *   - No diagnostic verbs: diagnose / treat / cure / prevent disease
 *   - Use: "support", "manage", "track", "optimize", "monitor", "improve"
 *   - Every AI screen must display AI_DISCLOSURE
 */

/** Constant disclosed on every screen that surfaces AI-generated content. */
export const AI_DISCLOSURE =
  "You're talking to an AI — this is wellness guidance, not medical advice.";

/** All static UI strings, organized by screen/domain. */
export const COPY = {
  app: {
    title: "LongevityOS",
    tagline: "Your personal wellness companion",
  },

  tabBar: {
    today: "Today",
    coach: "Coach",
    records: "Records",
    insights: "Insights",
    care: "Care",
    me: "Me",
  },

  auth: {
    login: {
      heading: "Welcome back",
      subheading: "Sign in to continue your wellness journey",
      cta: "Sign in",
      emailLabel: "Email",
      passwordLabel: "Password",
      forgotPassword: "Forgot password?",
      noAccount: "Don't have an account?",
      signUp: "Sign up",
    },
    logout: "Sign out",
  },

  onboarding: {
    steps: [
      {
        title: "Welcome to LongevityOS",
        body: "We'll help you build a clearer picture of your overall wellness.",
      },
      {
        title: "Connect your data",
        body: "Sync your wearables and health apps to get personalized insights.",
      },
      {
        title: "Set your goals",
        body: "Tell us what aspects of your wellbeing you'd like to improve.",
      },
      {
        title: "Meet your AI Coach",
        body: "You're talking to an AI — this is wellness guidance, not medical advice.",
      },
    ],
    cta: {
      next: "Next",
      back: "Back",
      finish: "Get started",
      skip: "Skip",
    },
  },

  today: {
    greeting: (name: string) => `Good morning, ${name}`,
    sections: {
      dailySnapshot: "Daily Snapshot",
      highlights: "Highlights",
      topActions: "Top Actions",
      recentActivity: "Recent Activity",
    },
    scoreLabel: "Wellness Score",
    streakLabel: "Day streak",
    noActivity: "No activity logged yet today.",
  },

  coach: {
    placeholder: "Ask me anything about your wellness journey",
    inputHint: "Type a message",
    sendButton: "Send",
    disclosure: "You're talking to an AI — this is wellness guidance, not medical advice.",
    sessionTitle: "AI Wellness Coach",
    loadingReply: "Thinking…",
    errorReply: "I wasn't able to retrieve a response right now. Please try again.",
  },

  records: {
    title: "Health Records",
    placeholder: "Ask a question about your records",
    disclosure: "You're talking to an AI — this is wellness guidance, not medical advice.",
    sections: {
      labResults: "Lab Results",
      vitals: "Vitals",
      medications: "Medications",
      vaccinations: "Vaccinations",
      visits: "Visits",
    },
    noRecords: "No records found.",
    uploadCta: "Upload a record",
  },

  insights: {
    title: "Insights",
    subtitle: "Understand the key dimensions of your wellness",
    dimensions: {
      sleep: "Sleep",
      activity: "Activity",
      nutrition: "Nutrition",
      stress: "Stress & Recovery",
      cardiovascular: "Cardiovascular",
      metabolic: "Metabolic Health",
      mentalWellness: "Mental Wellness",
      longevity: "Longevity Score",
    },
    noData: "Not enough data to generate insights yet.",
    disclosure: "You're talking to an AI — this is wellness guidance, not medical advice.",
  },

  care: {
    title: "Care Plan",
    subtitle: "Personalized wellness actions to support your goals",
    pillars: {
      movement: "Movement",
      rest: "Rest & Recovery",
      nourishment: "Nourishment",
      mindfulness: "Mindfulness",
      social: "Social Wellbeing",
      checkups: "Wellness Check-ups",
    },
    actionCompleted: "Marked as done",
    noPlan: "Your care plan is being prepared.",
    disclosure: "You're talking to an AI — this is wellness guidance, not medical advice.",
  },

  me: {
    title: "My Profile",
    sections: {
      account: "Account",
      privacy: "Privacy & Data",
      notifications: "Notifications",
      about: "About",
    },
    gdpr: {
      heading: "Your data rights",
      exportData: "Export my data",
      deleteAccount: "Delete my account",
      body: "You have the right to access, correct, or erase your personal data at any time under GDPR Art. 17.",
      confirmDelete: "Are you sure? This will permanently remove your account and all associated wellness data.",
    },
    versionLabel: "Version",
  },

  errors: {
    generic: "Something went wrong. Please try again.",
    network: "Unable to connect. Check your internet connection.",
    notFound: "Page not found.",
    unauthorized: "You need to sign in to continue.",
    sessionExpired: "Your session has expired. Please sign in again.",
    rateLimited: "Too many requests. Please wait a moment and try again.",
  },

  empty: {
    defaultTitle: "Nothing here yet",
    defaultBody: "Check back once you've synced some data.",
    coachHistory: "No conversations yet. Start chatting with your AI Coach.",
    records: "No health records uploaded yet.",
    insights: "Sync wearable data to unlock insights.",
    care: "Your personalized care plan will appear here.",
  },
} as const;

export type CopyType = typeof COPY;
