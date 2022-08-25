from .models import Meeting,Attendee,Flag,FlagAttempt


def validate_flag_attempt(meeting,attendee,attempted_code):
	error = None
	flag_attempt = None
	try:
		flag_attempt = FlagAttempt(code=attempted_code,user=attendee)
		flag = meeting.flag_set.get(code=attempted_code)
		# check if user has already flagged
		if( attendee.flagattempt_set.filter(correct_flag=flag)):
			error = 'already flagged'
		else:
			flag_attempt.correct_flag = flag
			attendee.score = attendee.score + flag.points
			# check if someone flagged before
			if(not flag.flagattempt_set.all()):
				attendee.score = attendee.score + flag.first_blood_reward
				flag_attempt.is_first_blood = True
			attendee.save()
		flag_attempt.save()
	except Flag.DoesNotExist:
		error = 'not found'
	return (flag_attempt,error)