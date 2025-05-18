from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from .models import HardQuestion, HardQuestionAttempt, Question, Choice, QuestionAttempt, TournamentAttempt, TournamentQuestion

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'date_of_birth', 'phone_number')
        read_only_fields = ('id',)

class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'password', 'password2', 'date_of_birth', 'phone_number')
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password
            )

            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

# Added serializers for questions
class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'index', 'is_correct']

class QuestionCreateSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)

        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)

        return question

class QuestionDisplaySerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    correct_choice = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'choices', 'correct_choice']

    def get_correct_choice(self, obj):
        try:
            # Get the first correct choice instead of expecting only one
            correct_choice = obj.choices.filter(is_correct=True).first()
            if correct_choice:
                return correct_choice.index
            return None
        except Exception:
            return None

class QuestionAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionAttempt
        fields = ['id', 'question', 'is_correct', 'created_at']
        read_only_fields = ['id', 'created_at']


# Tournament serializers
class TournamentQuestionSerializer(serializers.ModelSerializer):
    question_data = QuestionDisplaySerializer(source='question', read_only=True)

    class Meta:
        model = TournamentQuestion
        fields = ['id', 'question', 'question_data', 'answered', 'is_correct', 'position']
        read_only_fields = ['id', 'question', 'position']

class TournamentAttemptSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = TournamentAttempt
        fields = ['id', 'user_name', 'start_time', 'end_time', 'total_seconds',
                 'questions_count', 'correct_count', 'completed']
        read_only_fields = ['id', 'start_time', 'questions_count']

class LeaderboardEntrySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = TournamentAttempt
        fields = ['id', 'user_name', 'total_seconds', 'end_time']


class HardQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardQuestion
        fields = ['id', 'question_text', 'difficulty', 'created_at']
        read_only_fields = ['id', 'created_at']

class HardQuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardQuestion
        fields = ['id', 'question_text', 'correct_answer', 'difficulty', 'created_at']
        read_only_fields = ['id', 'created_at']

class HardQuestionAttemptSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)

    class Meta:
        model = HardQuestionAttempt
        fields = ['id', 'question', 'question_text', 'user_answer', 'is_correct', 'created_at']
        read_only_fields = ['id', 'created_at']