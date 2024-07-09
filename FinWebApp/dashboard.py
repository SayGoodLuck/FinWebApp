from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from rest_framework.decorators import api_view

from .models import PlaidToken, Transactions, Cards


@api_view(['GET'])
@login_required()
def get_dashboard(request):
    user = request.user
    plaid_token = PlaidToken.objects.filter(user_id=user).first()
    if plaid_token:
        transactions = Transactions.objects.filter(user_id=user).values(
            'user_id', 'bank', 'amount', 'merchant_name', 'category', 'date'
        )
        transactions_list = list(transactions)
        cards = Cards.objects.filter(user_id=user).values(
            'user_id', 'bank', 'card_name', 'card_number', 'card_type', 'balance', 'currency'
        )
        cards_list = list(cards)
        data = {
            'transactions': transactions_list,
            'cards': cards_list
        }

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Connect to your bank'}, status=404)
