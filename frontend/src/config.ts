export const CONFIG = {
  apiBase: import.meta.env.VITE_API_BASE as string,

  auth: {
    loginPath: "/auth/login",
    tokenField: "access_token",
  },

  habits: {
    listPath: "/habits",
    createPath: "/habits",
    deletePathTemplate: "/habits/{id}",
  },

  checkins: {
    createPath: "/checkins",
    habitResultsField: "habit_results",
    habitIdField: "habit_id",
    doneField: "done",
  },

  insights: {
    todayPath: "/insights/today",
    moodAvg7dField: "mood_avg_7d",
    habitStreaksJsonField: "habit_streaks_json",
  },
};
