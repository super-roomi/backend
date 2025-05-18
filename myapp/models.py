from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    def create_user(self, email, full_name, date_of_birth, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            full_name=full_name,
            date_of_birth=date_of_birth,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, date_of_birth, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, full_name, date_of_birth, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'date_of_birth']

    def __str__(self):
        return self.email

# Added models for questions
class Question(models.Model):
    question_text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    index = models.IntegerField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.question.question_text} - {self.text}"

    class Meta:
        unique_together = ['question', 'index']

class QuestionAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_str = self.user.email if self.user else "Anonymous"
        return f"{user_str} - {self.question.question_text} - {'Correct' if self.is_correct else 'Incorrect'}"
    

class TournamentAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournament_attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_seconds = models.FloatField(null=True, blank=True)
    questions_count = models.IntegerField(default=5)  # Default to 5 questions
    correct_count = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.full_name} - {self.total_seconds}s" if self.completed else f"{self.user.full_name} - In progress"
    
    class Meta:
        ordering = ['total_seconds', '-end_time']  # Sort by time (fastest first)

class TournamentQuestion(models.Model):
    tournament = models.ForeignKey(TournamentAttempt, on_delete=models.CASCADE, related_name='tournament_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answered = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=False)
    position = models.IntegerField()  # Position in the tournament (1-5)
    
    class Meta:
        ordering = ['position']
        unique_together = ['tournament', 'position']



class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']




class HardQuestion(models.Model):
    """Model for hard questions without multiple choices"""
    question_text = models.CharField(max_length=500)
    correct_answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.question_text

class HardQuestionAttempt(models.Model):
    """Model for tracking attempts at hard questions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hard_question_attempts')
    question = models.ForeignKey(HardQuestion, on_delete=models.CASCADE, related_name='attempts')
    user_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.question.question_text} - {'Correct' if self.is_correct else 'Incorrect'}"
    
    class Meta:
        ordering = ['-created_at']

class HardQuestion(models.Model):
    question_text = models.CharField(max_length=500)
    correct_answer = models.CharField(max_length=500)  # Exact answer
    difficulty = models.IntegerField(default=1)  # 1-5 scale
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text

class HardQuestionAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hard_question_attempts')
    question = models.ForeignKey(HardQuestion, on_delete=models.CASCADE)
    user_answer = models.CharField(max_length=500)  # User's submitted answer
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.question.question_text} - {'Correct' if self.is_correct else 'Incorrect'}"