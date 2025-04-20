import json
from channels.generic.websocket     import AsyncWebsocketConsumer
from web.models                     import Auction, Bids, Message, User
from django.utils                   import timezone
from datetime                       import datetime

class BidConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.auction_id = self.scope['url_route']['kwargs']['auction_id']
        self.room_group_name = f"auction_{self.auction_id}"

        # Join the auction group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the auction group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Receive a new bid from the WebSocket
        text_data_json = json.loads(text_data)
        bid_data = text_data_json['bid']
        auction_id = self.auction_id

        # Fetch Auction object to associate the bid
        auction = await Auction.objects.get(id=auction_id)

        # Create a new Bid object and save it
        bid = Bids(
            exporterId=bid_data['exporterId'],
            auctionID=auction,
            product_name=bid_data['product_name'],
            category=bid_data['category'],
            initial_price=bid_data['initial_price'],
            current_price=bid_data['current_price'],
            mmq=bid_data['mmq'],
            moq=bid_data['moq'],
            round=bid_data['round'],
            total_rounds=bid_data['total_rounds'],
            time_left=bid_data['time_left'],
            bidMMQ=bid_data['bidMMQ'],
            pricePerQuantity=bid_data['pricePerQuantity'],
            bidsMade=[],
            isEnded=False
        )
        # Save the bid to MongoDB
        await bid.save()

        # Send the new bid to all clients in the auction group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'bid_message',
                'bid': bid_data
            }
        )

    async def bid_message(self, event):
        # Send the bid message to WebSocket
        bid = event['bid']

        await self.send(text_data=json.dumps({
            'bid': bid
        }))

class MessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.auction_id = self.scope['url_route']['kwargs']['auction_id']
        self.room_group_name = f"messages_{self.auction_id}"

        # Join the message group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the message group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_data = text_data_json['message']

        # Fetch Auction object to associate the message
        auction = await Auction.objects.get(id=self.auction_id)

        # Create a new Message object and save it
        message = Message(
            auction=auction,
            sender_username=message_data['sender_username'],
            receiver_username=message_data['receiver_username'],
            message=message_data['message']
        )
        # Save the message to MongoDB
        await message.save()

        # Send the message to the WebSocket group (to notify all connected users)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_event',
                'message': message_data
            }
        )

    async def message_event(self, event):
        # Send the message to WebSocket
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))