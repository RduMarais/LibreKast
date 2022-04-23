from django.db import models
from django.utils.translation import gettext as _


class TeamMember(models.Model):
    title = models.CharField('Name', max_length=20)
    role = models.CharField('Role', max_length=20)
    bio = models.CharField('About', max_length=50)
    imgUrl = models.URLField('Image URL')

    def __str__(self):
        return self.title

class HomePage(models.Model):
    name=models.CharField(_('URL identifier of the page'),max_length=15,unique=True,default='index')
    topTitle_ln1=models.CharField(_('Title (first line)'),default="LibreKast Meetings", max_length=30)
    topTitle_ln2=models.CharField(_('Title (second line)'),default="Gamify your meetings",max_length=30)
    image = models.ImageField(_('Image for your page'),null = True,blank=True)
    topDes=models.TextField(_('App Description'),default="Create animations for your meetings such as Quizzes, Polls and Word Clouds. This application is a dummy app showcasing the functionalities. Please bear in mind that this code is made free to help but this app was not designed by actual devs.",max_length=300)
    btn2Text=models.CharField(_('Button 2 Text'),default="Know More",max_length=30)
    btn2Url=models.CharField(_('Button 2 URL'),default=" https://github.com/RduMarais/LibreKast",max_length=40)
    teamTitle=models.CharField(_('Title 2nd paragraph'),default="State of the development ",max_length=30)
    teamDesc=models.TextField(_('Content 2nd paragraph'),default="The current app was designed by Romain du Marais for personal use and shared publicly on GitHub ; and Aahnik Daw for a school project. Please contribute to its development if you consider it useful.",max_length=300)

    class Meta:
        verbose_name = _('Page')
        verbose_name_plural = _('Pages')

