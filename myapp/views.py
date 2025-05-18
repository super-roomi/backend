from django.db.models import F  
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import permissions
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
import random
from django.db import transaction
from django.utils import timezone
from .models import HardQuestion, HardQuestionAttempt, Question, Choice, QuestionAttempt, TournamentAttempt, TournamentQuestion, UserAnswer
from .models import Question, Choice, QuestionAttempt, TournamentAttempt, TournamentQuestion, UserAnswer
from .serializers import (
    HardQuestionAttemptSerializer, HardQuestionCreateSerializer, HardQuestionSerializer, LeaderboardEntrySerializer, RegisterSerializer, LoginSerializer, TournamentQuestionSerializer, UserSerializer,
    QuestionCreateSerializer, QuestionDisplaySerializer, QuestionAttemptSerializer
)

User = get_user_model()

# Authentication views
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class QuestionCreateAPIView(APIView):
    """
    API for creating math questions (backend access only)
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        # First validate the question data
        serializer = QuestionCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Check if choices were provided
        choices_data = request.data.get('choices', [])
        if not choices_data or len(choices_data) < 2:
            return Response(
                {"error": "At least two choices must be provided for a question"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure only one choice is marked correct
        correct_choices = [c for c in choices_data if c.get('is_correct')]

        if len(correct_choices) == 0:
            return Response(
                {"error": "At least one choice must be marked as correct"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(correct_choices) > 1:
            return Response(
                {"error": "Only one choice should be marked as correct"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the question first
        question = Question.objects.create(
            question_text=serializer.validated_data['question_text']
        )

        # Then add all the choices
        for choice_data in choices_data:
            Choice.objects.create(
                question=question,
                text=choice_data.get('text', ''),
                index=choice_data.get('index', 0),
                is_correct=choice_data.get('is_correct', False)
            )

        # Return the created question with all its choices
        result_serializer = QuestionCreateSerializer(question)
        return Response(
            result_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def get(self, request):
        """List all questions (admin only)"""
        questions = Question.objects.all().order_by('-created_at')
        serializer = QuestionCreateSerializer(questions, many=True)
        return Response(serializer.data)

    def delete(self, request):
        """Delete a question (admin only)"""
        question_id = request.query_params.get('id')
        if not question_id:
            return Response(
                {"error": "Question ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            question = Question.objects.get(id=question_id)
            question.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Question.DoesNotExist:
            return Response(
                {"error": "Question not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
class RandomQuestionAPIView(APIView):
    """
    API for getting a random question for students
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        question_count = Question.objects.count()
        if question_count == 0:
            return Response(
                {"error": "No questions available"},
                status=status.HTTP_404_NOT_FOUND
            )

        random_index = random.randint(0, question_count - 1)
        question = Question.objects.all()[random_index]
        serializer = QuestionDisplaySerializer(question)
        return Response(serializer.data)

class QuestionAttemptAPIView(APIView):
    """
    API for submitting question attempts and tracking progress
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question_id = request.data.get('question_id')
        is_correct = request.data.get('is_correct')
        selected_choice_id = request.data.get('selected_choice_id')

        question = get_object_or_404(Question, id=question_id)

        # Create the question attempt record
        attempt = QuestionAttempt.objects.create(
            user=request.user,
            question=question,
            is_correct=is_correct
        )

        # Also record in UserAnswer for comprehensive progress tracking
        if selected_choice_id:
            selected_choice = get_object_or_404(Choice, id=selected_choice_id)
            UserAnswer.objects.create(
                user=request.user,
                question=question,
                selected_choice=selected_choice,
                is_correct=is_correct
            )

        serializer = QuestionAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class PublicQuestionAttemptAPIView(APIView):
    """
    Public API for submitting question attempts without authentication
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        question_id = request.data.get('question_id')
        is_correct = request.data.get('is_correct')
        selected_choice_id = request.data.get('selected_choice_id')

        if question_id is None or is_correct is None:
            return Response(
                {"error": "Both question_id and is_correct are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        question = get_object_or_404(Question, id=question_id)

        # Get user if authenticated
        user = request.user if request.user.is_authenticated else None

        # Create the question attempt record
        attempt = QuestionAttempt.objects.create(
            user=user,
            question=question,
            is_correct=is_correct
        )

        # Also record in UserAnswer if authenticated and choice provided
        if user and selected_choice_id:
            selected_choice = get_object_or_404(Choice, id=selected_choice_id)
            UserAnswer.objects.create(
                user=user,
                question=question,
                selected_choice=selected_choice,
                is_correct=is_correct
            )

        serializer = QuestionAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UserProgressAPIView(APIView):
    """
    API for getting a user's progress
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Get user's attempts
        attempts = QuestionAttempt.objects.filter(user=request.user)
        total_attempts = attempts.count()
        correct_attempts = attempts.filter(is_correct=True).count()

        return Response({
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts,
            'accuracy': float(correct_attempts) / total_attempts if total_attempts > 0 else 0
        })
    


class LeaderboardAPIView(APIView):
    """
    Get the top 5 fastest tournament completions
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Get only completed tournaments with all correct answers
        leaderboard = TournamentAttempt.objects.filter(
            completed=True,
            correct_count=F('questions_count')
        ).order_by('total_seconds')[:5]

        serializer = LeaderboardEntrySerializer(leaderboard, many=True)
        return Response(serializer.data)

class StartTournamentAPIView(APIView):
    """
    Start a new tournament with 5 random questions
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Check if user already has an active tournament
        active_tournament = TournamentAttempt.objects.filter(
            user=request.user,
            completed=False
        ).first()

        if active_tournament:
            # Return the existing tournament instead of creating a new one
            return Response({
                "tournament_id": active_tournament.id,
                "start_time": active_tournament.start_time,
                "message": "You already have an active tournament"
            })

        # Create new tournament attempt
        tournament = TournamentAttempt.objects.create(
            user=request.user,
            questions_count=5
        )

        # Select 5 random questions
        question_count = Question.objects.count()
        if question_count < 5:
            tournament.delete()
            return Response(
                {"error": "Not enough questions available for a tournament (need at least 5)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get random questions without repetition
        all_questions = list(Question.objects.all())
        selected_questions = random.sample(all_questions, 5)

        # Create tournament questions
        for i, question in enumerate(selected_questions):
            TournamentQuestion.objects.create(
                tournament=tournament,
                question=question,
                position=i+1
            )

        return Response({
            "tournament_id": tournament.id,
            "start_time": tournament.start_time
        }, status=status.HTTP_201_CREATED)

class GetTournamentQuestionsAPIView(APIView):
    """
    Get all questions for a specific tournament
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, tournament_id):
        try:
            tournament = TournamentAttempt.objects.get(id=tournament_id, user=request.user)

            # Check if tournament is already completed
            if tournament.completed:
                return Response(
                    {"error": "This tournament is already completed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            questions = TournamentQuestion.objects.filter(tournament=tournament)

            # Check if questions exist
            if not questions.exists():
                return Response(
                    {"error": "No questions found for this tournament"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = TournamentQuestionSerializer(questions, many=True)
            return Response(serializer.data)

        except TournamentAttempt.DoesNotExist:
            return Response(
                {"error": "Tournament not found or not authorized"},
                status=status.HTTP_404_NOT_FOUND
            )

class SubmitTournamentAnswerAPIView(APIView):
    """
    Submit an answer for a tournament question
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            tournament_question_id = request.data.get('tournament_question_id')
            selected_choice_id = request.data.get('selected_choice_id')

            if not tournament_question_id or not selected_choice_id:
                return Response(
                    {"error": "Both tournament_question_id and selected_choice_id are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                tournament_question = TournamentQuestion.objects.get(id=tournament_question_id)
            except TournamentQuestion.DoesNotExist:
                return Response(
                    {"error": f"Tournament question not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if this is the user's tournament
            if tournament_question.tournament.user != request.user:
                return Response(
                    {"error": "Not authorized to answer this tournament question"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if the answer is correct
            try:
                selected_choice = Choice.objects.get(id=selected_choice_id)
            except Choice.DoesNotExist:
                return Response(
                    {"error": f"Choice not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Make sure the choice belongs to this question
            if selected_choice.question.id != tournament_question.question.id:
                return Response(
                    {"error": "Selected choice does not belong to this question"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update the question's status
            is_correct = selected_choice.is_correct

            # If this answer is correct (and wasn't already marked correct), increment the count
            if is_correct and not tournament_question.is_correct:
                tournament_question.is_correct = True
                tournament_question.answered = True
                tournament_question.save()

                # Increment correct_count
                tournament_question.tournament.correct_count += 1
                tournament_question.tournament.save()
            else:
                # For wrong answers, mark as answered
                tournament_question.answered = True
                tournament_question.save()

            # Record in UserAnswer for progress tracking
            UserAnswer.objects.create(
                user=request.user,
                question=tournament_question.question,
                selected_choice=selected_choice,
                is_correct=is_correct
            )

            # Get correct choice
            try:
                correct_choice = tournament_question.question.choices.get(is_correct=True)
                correct_choice_id = correct_choice.id
            except (Choice.DoesNotExist, Choice.MultipleObjectsReturned):
                # Handle case where no correct choice or multiple correct choices
                choices = tournament_question.question.choices.filter(is_correct=True)
                correct_choice_id = choices.first().id if choices.exists() else None

            return Response({
                "is_correct": is_correct,
                "correct_choice_id": correct_choice_id
            })

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in SubmitTournamentAnswerAPIView: {str(e)}")

            return Response(
                {"error": "An unexpected error occurred. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        


class CompleteTournamentAPIView(APIView):
    """
    Complete a tournament and record results
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            tournament_id = request.data.get('tournament_id')
            time_spent = request.data.get('time_spent')  # in seconds

            if not tournament_id:
                return Response(
                    {"error": "tournament_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                tournament = TournamentAttempt.objects.get(id=tournament_id, user=request.user)
            except TournamentAttempt.DoesNotExist:
                return Response(
                    {"error": f"Tournament with ID {tournament_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Mark tournament as completed
            tournament.completed = True

            # Set end time
            tournament.end_time = timezone.now()

            # Record time spent
            if time_spent is not None:
                tournament.total_seconds = float(time_spent)

            tournament.save()

            # Verify correct count
            correct_count = tournament.tournament_questions.filter(is_correct=True).count()
            tournament.correct_count = correct_count
            tournament.save()

            return Response({
                "message": "Tournament completed successfully",
                "tournament_id": tournament.id,
                "correct_count": tournament.correct_count,
                "total_questions": tournament.questions_count,
                "time_spent": tournament.total_seconds,
                "phone_number": tournament.id*200
            })

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in CompleteTournamentAPIView: {str(e)}")
            logger.error(f"Request data: {request.data}")

            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        

class GetActiveTournamentAPIView(APIView):
    """
    Get the user's currently active tournament, if any
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Find active (incomplete) tournaments for this user
        active_tournament = TournamentAttempt.objects.filter(
            user=request.user,
            completed=False
        ).order_by('-start_time').first()

        if active_tournament:
            return Response({
                "tournament_id": active_tournament.id,
                "start_time": active_tournament.start_time,
                "questions_count": active_tournament.questions_count
            })
        else:
            return Response({"message": "No active tournament found"}, status=status.HTTP_404_NOT_FOUND)        








from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from datetime import timedelta

class UserProgressAPIView(APIView):
    """Get detailed user progress statistics compared to other users"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())

        # Count regular question answers (non-tournament)
        user_answers = UserAnswer.objects.filter(user=user)
        weekly_user_answers = user_answers.filter(created_at__date__gte=start_of_week)

        # Calculate personal stats
        total_answers = user_answers.count()
        correct_answers = user_answers.filter(is_correct=True).count()

        weekly_answers = weekly_user_answers.count()
        weekly_correct = weekly_user_answers.filter(is_correct=True).count()

        # Tournament stats
        tournament_attempts = TournamentAttempt.objects.filter(user=user).count()
        completed_tournaments = TournamentAttempt.objects.filter(user=user, completed=True).count()

        # Calculate app-wide averages
        active_users = User.objects.filter(
            Q(answers__isnull=False) | Q(tournament_attempts__isnull=False)
        ).distinct().count()

        if active_users == 0:
            active_users = 1  # Prevent division by zero

        # App-wide averages
        all_answers = UserAnswer.objects.count()
        all_weekly_answers = UserAnswer.objects.filter(created_at__date__gte=start_of_week).count()
        all_correct_answers = UserAnswer.objects.filter(is_correct=True).count()

        # Average stats per user
        avg_answers_per_user = all_answers / active_users
        avg_weekly_answers = all_weekly_answers / active_users

        # App correct percentage
        app_correct_pct = (all_correct_answers / all_answers * 100) if all_answers > 0 else 0

        # Tournament stats
        all_tournaments = TournamentAttempt.objects.count()
        avg_tournaments_per_user = all_tournaments / active_users

        # Average tournament times
        avg_tournament_time = TournamentAttempt.objects.filter(
            user=user, completed=True
        ).aggregate(avg_time=Avg('total_seconds'))['avg_time'] or 0

        app_avg_time = TournamentAttempt.objects.filter(
            completed=True
        ).aggregate(avg_time=Avg('total_seconds'))['avg_time'] or 0

        # Get best tournament time
        best_tournament = TournamentAttempt.objects.filter(
            user=user, completed=True
        ).order_by('total_seconds').first()

        # Add hard questions statistics
        hard_question_attempts = HardQuestionAttempt.objects.filter(user=user)
        hard_total_attempts = hard_question_attempts.count()
        hard_correct_attempts = hard_question_attempts.filter(is_correct=True).count()
        hard_weekly_attempts = hard_question_attempts.filter(created_at__date__gte=start_of_week).count()
        hard_weekly_correct = hard_question_attempts.filter(created_at__date__gte=start_of_week, is_correct=True).count()

        # Calculate app-wide hard question stats
        all_hard_attempts = HardQuestionAttempt.objects.count()
        all_hard_correct = HardQuestionAttempt.objects.filter(is_correct=True).count()
        hard_active_users = User.objects.filter(hard_question_attempts__isnull=False).distinct().count() or 1

        return Response({
            "personal_stats": {
                "total_problems_solved": total_answers,
                "correct_percentage": (correct_answers / total_answers * 100) if total_answers > 0 else 0,
                "problems_solved_this_week": weekly_answers,
                "correct_this_week": weekly_correct,
                "weekly_percentage": (weekly_correct / weekly_answers * 100) if weekly_answers > 0 else 0,

                "tournament_attempts": tournament_attempts,
                "completed_tournaments": completed_tournaments,
                "tournaments_this_week": TournamentAttempt.objects.filter(
                    user=user, start_time__date__gte=start_of_week
                ).count(),

                "avg_tournament_time": avg_tournament_time,
                "best_tournament_time": best_tournament.total_seconds if best_tournament else None,

                # Hard questions statistics
                "hard_questions": {
                    "total_attempts": hard_total_attempts,
                    "correct_attempts": hard_correct_attempts,
                    "accuracy": (hard_correct_attempts / hard_total_attempts * 100) if hard_total_attempts > 0 else 0,
                    "this_week": hard_weekly_attempts,
                    "correct_this_week": hard_weekly_correct,
                    "weekly_percentage": (hard_weekly_correct / hard_weekly_attempts * 100) if hard_weekly_attempts > 0 else 0,
                }
            },
            "app_averages": {
                "avg_problems_per_user": avg_answers_per_user,
                "avg_problems_this_week": avg_weekly_answers,
                "avg_correct_percentage": app_correct_pct,
                "avg_tournaments_per_user": avg_tournaments_per_user,
                "avg_tournament_time": app_avg_time,

                # Hard questions app-wide averages
                "hard_questions": {
                    "avg_attempts_per_user": all_hard_attempts / hard_active_users,
                    "avg_correct_percentage": (all_hard_correct / all_hard_attempts * 100) if all_hard_attempts > 0 else 0
                }
            }
        })    


# Add to views.py
class QuizResultAPIView(APIView):
    """
    API for submitting quiz results
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        score = request.data.get('score')
        total = request.data.get('total')
        questions_data = request.data.get('questions', [])

        if score is None or total is None:
            return Response(
                {"error": "Both score and total are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Record individual question attempts
        for question_data in questions_data:
            question_id = question_data.get('question_id')
            is_correct = question_data.get('is_correct')
            selected_choice_id = question_data.get('selected_choice_id')

            if question_id and is_correct is not None:
                question = get_object_or_404(Question, id=question_id)

                # Create question attempt
                attempt = QuestionAttempt.objects.create(
                    user=request.user,
                    question=question,
                    is_correct=is_correct
                )

                # Also record in UserAnswer
                if selected_choice_id:
                    try:
                        selected_choice = Choice.objects.get(id=selected_choice_id)
                        UserAnswer.objects.create(
                            user=request.user,
                            question=question,
                            selected_choice=selected_choice,
                            is_correct=is_correct
                        )
                    except Choice.DoesNotExist:
                        pass  # Skip if choice doesn't exist

        return Response({
            "message": "Quiz results recorded successfully",
            "score": score,
            "total": total
        }, status=status.HTTP_201_CREATED)
    
class MultipleRandomQuestionsAPIView(APIView):
    """
    API for getting multiple random questions for quizzes
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        count = int(request.query_params.get('count', 10))  # Default to 10 questions

        # Limit the maximum number of questions
        if count > 20:
            count = 20

        question_count = Question.objects.count()
        if question_count == 0:
            return Response(
                {"error": "No questions available"},
                status=status.HTTP_404_NOT_FOUND
            )

        # If we have fewer questions than requested, return all available
        if question_count <= count:
            questions = Question.objects.all()
        else:
            # Get random questions without repetition
            questions = list(Question.objects.all())
            questions = random.sample(questions, count)

        serializer = QuestionDisplaySerializer(questions, many=True)
        return Response(serializer.data)
    

class UserProfileAPIView(APIView):
    """
    API for viewing, updating and deleting a user's profile
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user profile data"""
        user = request.user
        
        return Response({
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'date_of_birth': user.date_of_birth,
            'phone_number': user.phone_number,
            'created_at': user.created_at,
            'is_staff': user.is_staff
        })

    def put(self, request):
        """Update user profile"""
        user = request.user
        
        # Extract data from request
        email = request.data.get('email')
        full_name = request.data.get('full_name')
        date_of_birth = request.data.get('date_of_birth')
        phone_number = request.data.get('phone_number')
        
        # Validate email uniqueness if changing
        if email and email != user.email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({'error': 'Email already in use'}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
            
        # Update other fields
        if full_name:
            user.full_name = full_name
            
        if date_of_birth:
            user.date_of_birth = date_of_birth
            
        if phone_number is not None:  # Allow empty string to clear phone
            user.phone_number = phone_number
        
        try:
            user.save()
            return Response({
                'message': 'Profile updated successfully',
                'email': user.email,
                'full_name': user.full_name,
                'date_of_birth': user.date_of_birth,
                'phone_number': user.phone_number
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Delete user account"""
        try:
            user = request.user
            user.delete()
            return Response({'message': 'Account deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        



class HardQuestionCreateAPIView(APIView):
    """
    API for creating hard questions (admin only)
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = HardQuestionCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """List all hard questions (admin only)"""
        questions = HardQuestion.objects.all().order_by('-created_at')
        serializer = HardQuestionCreateSerializer(questions, many=True)
        return Response(serializer.data)

    def delete(self, request):
        """Delete a hard question (admin only)"""
        question_id = request.query_params.get('id')
        if not question_id:
            return Response(
                {"error": "Question ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            question = HardQuestion.objects.get(id=question_id)
            question.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except HardQuestion.DoesNotExist:
            return Response(
                {"error": "Question not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class RandomHardQuestionsAPIView(APIView):
    """
    API for getting random hard questions
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        count = int(request.query_params.get('count', 5))  # Default to 5 questions

        # Limit the maximum number
        if count > 10:
            count = 10

        question_count = HardQuestion.objects.count()
        if question_count == 0:
            return Response(
                {"error": "No hard questions available"},
                status=status.HTTP_404_NOT_FOUND
            )

        # If we have fewer questions than requested, return all available
        if question_count <= count:
            questions = HardQuestion.objects.all()
        else:
            # Get random questions without repetition
            questions = list(HardQuestion.objects.all())
            questions = random.sample(questions, count)

        serializer = HardQuestionSerializer(questions, many=True)
        return Response(serializer.data)

class HardQuestionAttemptAPIView(APIView):
    """
    API for submitting hard question attempts
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question_id = request.data.get('question_id')
        user_answer = request.data.get('user_answer')

        if not question_id or user_answer is None:
            return Response(
                {"error": "Both question_id and user_answer are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            question = HardQuestion.objects.get(id=question_id)
        except HardQuestion.DoesNotExist:
            return Response(
                {"error": "Question not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Normalize the answers for comparison (convert to lowercase and strip whitespace)
        correct_answer = question.correct_answer.lower().strip()
        provided_answer = user_answer.lower().strip()

        # Check if the answer is correct
        is_correct = (provided_answer == correct_answer)

        # Create the attempt record
        attempt = HardQuestionAttempt.objects.create(
            user=request.user,
            question=question,
            user_answer=user_answer,
            is_correct=is_correct
        )

        # Return the result
        serializer = HardQuestionAttemptSerializer(attempt)
        return Response({
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,  # Always show correct answer
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)


class PublicHardQuestionAttemptAPIView(APIView):
    """
    Public API for submitting hard question attempts without authentication
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        question_id = request.data.get('question_id')
        user_answer = request.data.get('user_answer')

        if not question_id or user_answer is None:
            return Response(
                {"error": "Both question_id and user_answer are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            question = HardQuestion.objects.get(id=question_id)
        except HardQuestion.DoesNotExist:
            return Response(
                {"error": "Question not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Normalize the answers for comparison
        correct_answer = question.correct_answer.lower().strip()
        provided_answer = user_answer.lower().strip()

        # Check if the answer is correct
        is_correct = (provided_answer == correct_answer)

        # Create the attempt record if user is authenticated
        user = request.user if request.user.is_authenticated else None

        if user:
            attempt = HardQuestionAttempt.objects.create(
                user=user,
                question=question,
                user_answer=user_answer,
                is_correct=is_correct
            )
            serializer = HardQuestionAttemptSerializer(attempt)
            response_data = serializer.data
        else:
            # For anonymous users, don't create a record but still give feedback
            response_data = {
                "question_id": question_id,
                "user_answer": user_answer
            }

        # Return the result
        return Response({
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,  # Always show correct answer
            "data": response_data
        }, status=status.HTTP_200_OK)
    
class HardQuizResultAPIView(APIView):
    """
    API for submitting hard quiz results
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        score = request.data.get('score')
        total = request.data.get('total')
        questions_data = request.data.get('questions', [])

        if score is None or total is None:
            return Response(
                {"error": "Both score and total are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Record individual question attempts
        for question_data in questions_data:
            question_id = question_data.get('question_id')
            user_answer = question_data.get('user_answer')
            is_correct = question_data.get('is_correct')

            if question_id and user_answer is not None and is_correct is not None:
                try:
                    question = HardQuestion.objects.get(id=question_id)

                    # Create question attempt
                    HardQuestionAttempt.objects.create(
                        user=request.user,
                        question=question,
                        user_answer=user_answer,
                        is_correct=is_correct
                    )
                except HardQuestion.DoesNotExist:
                    pass  # Skip if question doesn't exist

        return Response({
            "message": "Hard quiz results recorded successfully",
            "score": score,
            "total": total
        }, status=status.HTTP_201_CREATED)