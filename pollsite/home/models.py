from django.db import models


class TeamMember(models.Model):
    title = models.CharField('Name', max_length=20)
    role = models.CharField('Role', max_length=20)
    bio = models.CharField('About', max_length=50)
    imgUrl = models.URLField('Image URL')

    def __str__(self):
        return self.title

class HomePage(models.Model):
    topTitle_ln1=models.CharField('Title (first line)',default="LibreKast Meetings", max_length=30)
    topTitle_ln2=models.CharField('Title (second line)',default="Gamify your meetings",max_length=30)
    topDes=models.TextField('App Description',default="Create animations for your meetings such as Quizzes, Polls and Word Clouds. This application is a dummy app showcasing the functionalities. Please bear in mind that this code is made free to help but this app was not designed by actual devs.",max_length=300)
    btn1Text=models.CharField('Button 1 Text',default=" Vote Now",max_length=30)
    btn2Text=models.CharField('Button 2 Text',default=" Know More",max_length=30)
    btn2Url=models.CharField('Button 2 URL',default=" https://github.com/RduMarais/LibreKast",max_length=40)
    midTitle=models.CharField('Title 1st paragraph',default="How to deploy",max_length=30)
    midDesc=models.TextField('Content 1st paragraph',default="A comprehensive guide to deployment is available on GitHub README. In order to setup LibreKast in an deployment envionment, one needs to setup a web server (such as Apache or Nginx), setup the server for delivering a django app and clone the repository to start the app. Then for deployment a comprehensive checklist is available on GitHub to explain how to seed the application secrets; remove debugging functionalities; create an admin user etc.",max_length=600)
    teamTitle=models.CharField('Title 2nd paragraph',default="State of the development ",max_length=30)
    teamDesc=models.TextField('Content 2nd paragraph',default="The current app was designed by Romain du Marais for personal use and shared publicly on GitHub ; and Aahnik Daw for a school project. Please contribute to its development if you consider it useful.",max_length=300)
