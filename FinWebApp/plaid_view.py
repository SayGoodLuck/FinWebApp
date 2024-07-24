import json
import logging
import random

import plaid
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render
from plaid import configuration
from plaid.api import plaid_api
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from .models import Card, PlaidToken, Transaction

logger = logging.getLogger(__name__)

config = configuration.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': '6661f534de9928001b9a0c30',
        'secret': '8ae6520be19cf7ccad4b281f6a2875',
    }
)

api_client = plaid.ApiClient(config)
client = plaid_api.PlaidApi(api_client)

BANK_NAME = ['PKO Bank Polski', 'ING', 'BNP Paribas', 'Santander', 'Millenium', 'BelBa', 'Prior', 'Prez',
             'RusTehNo', 'moneyBank']
BANKS_DICT = {}


@login_required()
def initialize_plaid_link(request):
    try:
        link_token_response = LinkTokenCreateRequest(
            products=[Products('auth'), Products('transactions')],
            client_name="wallet",
            country_codes=[CountryCode('PL')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=request.user.username
            )

        )

        response = client.link_token_create(link_token_response)

        return JsonResponse({'link_token': response['link_token']})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
                return JsonResponse({"error": "this user have a access token"})
            else:

                PlaidToken.objects.create(
                    user_id=user_instance,
                    access_token=access_token
                )
                return JsonResponse({'success': True, 'access_token': access_token, 'name': user_instance.username})
        except plaid.ApiException as e:
            return JsonResponse({'error': str(e)}, status=400)


def index(request):
    return render(request, 'index.html')


@login_required()
def get_transactions(request):
    if request.method == 'GET':
        try:
            user_access_token = PlaidToken.objects.filter(user_id=request.user.id).first()
            access_token = user_access_token.access_token

            has_more = True

            # cursor for fetching any future updates after the latest update
            cursor = get_latest_cursor(request.user)

            # Iterate through each page of new transaction updates for item
            while has_more:
                if cursor is None:
                    sync_request = TransactionsSyncRequest(
                        access_token=access_token

                    )
                else:
                    sync_request = TransactionsSyncRequest(
                        access_token=access_token,
                        cursor=cursor

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
                Transaction.objects.create(
                    user_id=request.user,
                    bank=upd_bank(txn['account_id'], random.choice(BANK_NAME)),
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


# Cursor for control transactions update
def get_latest_cursor(user_id):
    try:
        plaid_cursor = PlaidToken.objects.filter(user_id=user_id).first()
        return plaid_cursor.cursor
    except PlaidToken.DoesNotExist:
        return None


# Cursor for control transactions update
def update_cursor(user_id, new_cursor):
    try:
        plaid_cursor = PlaidToken.objects.filter(user_id=user_id).first()
        plaid_cursor.cursor = new_cursor
        plaid_cursor.save()
    except PlaidToken.DoesNotExist:
        pass


# Json serialize func for POSTMAN response
def serialize_transaction(transaction):
    return {

        'bank': transaction['account_id'],
        'amount': transaction['amount'],
        'date': transaction['date'],
        'name': transaction['name'],
        'category': transaction['category']

    }


@login_required()
def get_balance(request):
    if request.method == 'GET':
        try:
            plaid_token = PlaidToken.objects.filter(user_id=request.user.id).first()
            access_token = plaid_token.access_token

            has_more = True

            # cursor for fetching any future updates after the latest update
            cursor = get_latest_cursor(request.user)

            while has_more:
                if cursor is None:
                    balance_request = AccountsBalanceGetRequest(access_token=access_token)
                    response = client.accounts_balance_get(balance_request)
                else:
                    balance_request = AccountsBalanceGetRequest(
                        access_token=access_token,
                        cursor=cursor
                    )
                    response = client.accounts_balance_get(balance_request)

                accounts = response["accounts"]

                accs_serialized = [serialize_accounts(txn) for txn in accounts]
                for data in accounts:
                    Card.objects.create(
                        user_id=request.user,
                        bank=upd_bank(data['account_id'], random.choice(BANK_NAME)),
                        card_type=data['type'],
                        card_name=data['name'],
                        card_number=data['mask'],
                        balance=data['balances']['current'],
                        currency=data['balances']['iso_currency_code']
                    )
                update_cursor(request.user, cursor)
                return JsonResponse(accs_serialized, safe=False)

        except PlaidToken.DoesNotExist:
            return JsonResponse({'error': 'PlaidToken not found for this user'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


def upd_bank(old, new):
    if old in BANKS_DICT:
        return BANKS_DICT[old]
    else:
        BANKS_DICT[old] = new
        return new


# Json serialize func for POSTMAN response
def serialize_accounts(acc):
    return {
        "bank": acc['account_id'],
        "card_name": acc['name'],
        "card_number": acc['mask'],
        "balance": acc['balances']['current'],
        "currency": acc['balances']["iso_currency_code"]
    }

#Main user page
def get_dashboard(request):
    if request.method == 'GET':
        get_transactions(request)
        get_balance(request)
        user = request.user
        plaid_token = PlaidToken.objects.filter(user_id=user).first()
        if plaid_token:
            transactions = Transaction.objects.filter(user_id=user).values(
                'bank', 'amount', 'merchant_name', 'category', 'date'
            )
            transactions_list = list(transactions)
            cards = Card.objects.filter(user_id=user).values(
                'bank', 'card_name', 'card_number', 'card_type', 'balance', 'currency'
            )
            cards_list = list(cards)
            data = {
                'transactions': transactions_list,
                'cards': cards_list
            }

            return JsonResponse(data, safe=False)
        else:
            return JsonResponse({'error': 'Connect to your bank'}, status=404)
