from django.urls import path
from .views import (
    CompleteTournamentAPIView, GetActiveTournamentAPIView, GetTournamentQuestionsAPIView, HardQuestionAttemptAPIView, HardQuestionCreateAPIView, HardQuizResultAPIView, LeaderboardAPIView, MultipleRandomQuestionsAPIView, PublicHardQuestionAttemptAPIView, QuizResultAPIView, RandomHardQuestionsAPIView, RegisterView, LoginView,
    QuestionCreateAPIView, RandomQuestionAPIView,
    QuestionAttemptAPIView, PublicQuestionAttemptAPIView, StartTournamentAPIView, SubmitTournamentAnswerAPIView, UserProfileAPIView,
    UserProgressAPIView, 
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    # Question-related endpoints
    path('questions/create/', QuestionCreateAPIView.as_view(), name='create-question'),
    path('questions/random/', RandomQuestionAPIView.as_view(), name='random-question'),
    path('questions/attempt/', QuestionAttemptAPIView.as_view(), name='question-attempt'),
    path('questions/attempt/public/', PublicQuestionAttemptAPIView.as_view(), name='public-question-attempt'),
    path('user/progress/', UserProgressAPIView.as_view(), name='user-progress'),
    path('tournaments/leaderboard/', LeaderboardAPIView.as_view(), name='tournament-leaderboard'),
    path('tournaments/start/', StartTournamentAPIView.as_view(), name='tournament-start'),
    path('tournaments/<int:tournament_id>/questions/', GetTournamentQuestionsAPIView.as_view(), name='tournament-questions'),
    path('tournaments/submit-answer/', SubmitTournamentAnswerAPIView.as_view(), name='tournament-submit'),
    path('tournaments/<int:tournament_id>/complete/', CompleteTournamentAPIView.as_view(), name='tournament-complete'),
    path('tournaments/active/', GetActiveTournamentAPIView.as_view(), name='tournament-active'),
    path('user/progress/', UserProgressAPIView.as_view(), name='user-progress'),
    path('user/quiz-result/', QuizResultAPIView.as_view(), name='quiz-result'),
    path('tournaments/complete/', CompleteTournamentAPIView.as_view(), name='tournament-complete'),
    path('questions/random-multiple/', MultipleRandomQuestionsAPIView.as_view(), name='random-multiple-questions'),
    path('user/profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('hard-questions/create/', HardQuestionCreateAPIView.as_view(), name='create-hard-question'),
    path('hard-questions/random/', RandomHardQuestionsAPIView.as_view(), name='random-hard-questions'),
    path('hard-questions/attempt/', HardQuestionAttemptAPIView.as_view(), name='hard-question-attempt'),
    path('hard-questions/attempt/public/', PublicHardQuestionAttemptAPIView.as_view(), name='public-hard-question-attempt'),
    path('hard-questions/quiz-result/', HardQuizResultAPIView.as_view(), name='hard-quiz-result'),
]