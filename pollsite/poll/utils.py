from .models import Meeting,Attendee,Flag,FlagAttempt


def validate_flag_attempt(meeting,attendee_id,attempted_code):
	error = None
	flag_attempt = None
	try:
		attendee = meeting.attendee_set.get(pk=attendee_id)
		flag_attempt = FlagAttempt(code=attempted_code,user=attendee)
		flag = meeting.flag_set.get(code=attempted_code)
		# check if user has already flagged
		if( attendee.flagattempt_set.filter(correct_flag=flag)):
			error = 'already flagged'
		else:
			flag_attempt.correct_flag = flag
			attendee.score = attendee.score + flag.points
			attendee.save()
		flag_attempt.save()
	except Flag.DoesNotExist:
		error = 'not found'
	except Attendee.DoesNotExist:
		error = 'other meeting'
	return (flag_attempt,error)