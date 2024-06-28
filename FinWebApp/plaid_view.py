import json

import plaid
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from plaid.api import plaid_api
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from .models import Cards
from .models import PlaidToken
from .models import Transactions

configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': '6661f534de9928001b9a0c30',
        'secret': '8ae6520be19cf7ccad4b281f6a2875',
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)


@login_required()
def exchange_public_token(request):
    if request.method == 'POST':
        public_token = json.loads(request.body)['public_token']
        try:
            exchange_response = ItemPublicTokenExchangeRequest(
                public_token=public_token
            )
            response = client.item_public_token_exchange(exchange_response)

            access_token = response['access_token']
            user_instance = User.objects.get(pk=request.user.id)
            if PlaidToken.objects.filter(user_id=user_instance):
                return JsonResponse({"error": "this user have a public token"})
            else:

                PlaidToken.objects.create(
                    user_id=user_instance,
                    access_token=access_token
                )
                return JsonResponse({'success': True, 'access_token': access_token, 'name': user_instance.username})
        except plaid.ApiException as e:
            return JsonResponse({'error': str(e)}, status=400)


@login_required()
def get_transactions(request):
    if request.method == 'POST':
        try:
            user_access_token = PlaidToken.objects.filter(user_id=request.user.id).first()
            access_token = user_access_token.access_token

            has_more = True

            # cursor for fetching any future updates after the latest update
            cursor = get_latest_cursor(request.user.id)

            # Iterate through each page of new transaction updates for item
            while has_more:
                if cursor:
                    sync_request = TransactionsSyncRequest(
                        access_token=access_token

                    )
                else:
                    sync_request = TransactionsSyncRequest(
                        access_token=access_token,

                    )
                response = client.transactions_sync(sync_request)

                # Extract data from response and convert to JSON-friendly format

                added = response['added']
                modified = response['modified']
                removed = response['removed']

                has_more = response['has_more']
                cursor = response['next_cursor']

            # Save transactions to the database
            for txn in added:
                Transactions.objects.create(
                    user_id=request.user,
                    bank=txn['account_id'],
                    amount=txn['amount'],
                    merchant_name=txn['name'],
                    category=txn['category'],
                    date=txn['date']
                )

            update_cursor(request.user, cursor)

            # Serialize transactions to JSON-friendly format

            added_serialized = [serialize_transaction(txn) for txn in added]
            modified_serialized = [serialize_transaction(txn) for txn in modified]
            removed_serialized = removed  # Assuming removed transactions are just IDs

            # Prepare JSON response with transaction updates
            data = {

                'added': added_serialized,
                'modified': modified_serialized,
                'removed': removed_serialized,
                'success': True
            }

            return JsonResponse(data)

        except PlaidToken.DoesNotExist:
            return JsonResponse({'error': 'PlaidToken not found for this user'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


def get_latest_cursor(user_id):
    try:
        plaid_cursor = PlaidToken.objects.filter(user_id=user_id).first()
        return plaid_cursor.cursor
    except PlaidToken.DoesNotExist:
        return None


def update_cursor(user_id, new_cursor):
    try:
        plaid_cursor = PlaidToken.objects.filter(user_id=user_id).first()
        plaid_cursor.cursor = new_cursor
        plaid_cursor.save()
    except PlaidToken.DoesNotExist:
        pass


def serialize_transaction(transaction):

    return {

        'bank': transaction['account_id'],
        'amount': transaction['amount'],
        'date': transaction['date'],
        'name': transaction['name'],
        'category': transaction['category']

    }


@login_required()
def get_balances(request):
    if request.method == 'POST':


        plaid_token = PlaidToken.objects.filter(user_id=request.user.id).first()
        access_token = plaid_token.access_token
        balance_request = AccountsBalanceGetRequest(access_token=access_token)
        response = client.accounts_balance_get(balance_request)

        accounts = response["accounts"]

        accs_serialized = [serialize_accounts(txn) for txn in accounts]
        for data in accounts:
            Cards.objects.create(
                user_id=request.user,
                bank=data['account_id'],
                card_type=data['type'],
                card_name=data['name'],
                card_number=data['mask'],
                balance=data['balances']['current'],
                currency=data['balances']['iso_currency_code']
            )

        return JsonResponse(accs_serialized, safe=False)


def serialize_accounts(acc):

    return {
        "bank": acc['account_id'],
        "card_name": acc['name'],
        "card_number": acc['mask'],
        "balance": acc['balances']['current'],
        "currency": acc['balances']["iso_currency_code"]
    }
