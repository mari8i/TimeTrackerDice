from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

class TogglCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)    
    api_key = models.CharField(max_length=64, blank=True, default="")

    def __str__(self):
        return 'Credentials of user: ' + self.user.username
    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        TogglCredentials.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.togglcredentials.save()

class TogglAction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    project = models.IntegerField(null=True, default=None, blank=True)
    tags = models.CharField(max_length=256, blank=True, default="")
    
    def __str__(self):
        return self.user.username + ' - ' + self.name
    
class TogglMapping(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    face = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(8)])    
    action = models.ForeignKey(TogglAction, on_delete=models.CASCADE, null=True, default=None)

    class Meta:
        unique_together = (('user', 'face'),)

    def __str__(self):
        return 'User: ' + self.user.username + ' face: ' + str(self.face) + ' action: ' + str(self.action)

@receiver(post_save, sender=User)
def create_mappings(sender, instance, created, **kwargs):
    if created:
        for i in range(8):
            TogglMapping.objects.create(user=instance, face=i + 1)        

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
