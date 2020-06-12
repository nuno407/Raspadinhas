import peewee
from time import sleep
from datetime import datetime, timezone

import dateparser

db = peewee.SqliteDatabase("game.db")

mode = "sell"

class Base(peewee.Model):
    class Meta:
        database = db


class GameType(Base):
    gameUniqueId = peewee.TextField(primary_key=True)
    gameName = peewee.TextField()
    numberOfGamesPerBatch = peewee.IntegerField()
    pricePerPaperGame = peewee.IntegerField()


class GamePaper(Base):
    """This class represents the game paper that is delivered to the client

    :param Base: [description]
    :type Base: [type]
    """
    gameUniqueId = peewee.ForeignKeyField(GameType.gameUniqueId)
    gameBatchId = peewee.TextField()
    gamePaperId = peewee.TextField()
    gamePaperStatus = peewee.TextField()
    gameCreatedAt = peewee.DateTimeField()
    gameSoldAt = peewee.DateTimeField(null=True)
    SOLD = "SOLD"
    ON_SALE = "ON_SALE"
    


db.create_tables([GameType, GamePaper])

def registerNewGame(id):
    print("This is a new game! We should register it!")
    gameName = input("Name: ")
    numberOfGamesPerBatch = input("Paper per batch: ")
    pricePerGame = input("Price per paper game: ")
    return GameType.create(gameUniqueId=id, gameName=gameName, numberOfGamesPerBatch=numberOfGamesPerBatch, pricePerPaperGame=pricePerGame)

def registerNewBatch(gameTypeInst, batchId, current_stock):
    for i in current_stock or range(int(gameTypeInst.numberOfGamesPerBatch)):
        GamePaper.create(gameUniqueId=gameTypeInst.gameUniqueId, gameBatchId=batchId, gamePaperId=i, gamePaperStatus=GamePaper.ON_SALE, gameCreatedAt=datetime.now(tz=timezone.utc), gameSoldAt=None)

def createSaleReport(to_date, from_date):
    sales={}
    query = (
        GamePaper
        .select(
            peewee.fn.COUNT(GamePaper.id).alias('sum'),
            GamePaper.gameUniqueId,
            GamePaper.gamePaperStatus,
            GameType.gameName,
            GameType.pricePerPaperGame
        )
        .join(
            GameType,
            on=(GameType.gameUniqueId == GamePaper.gameUniqueId)
        )
        .group_by(
            GamePaper.gameUniqueId,
            GamePaper.gamePaperStatus,
            GamePaper.gameBatchId
        )
        .where(((GamePaper.gameSoldAt>>None) | (GamePaper.gameSoldAt>=from_date & GamePaper.gameSoldAt<=to_date)) & (GamePaper.gameCreatedAt<=to_date))
    )

    for game in query.dicts():
        sale_type = sales.setdefault(game["gameUniqueId"], {"gameName": game["gameName"], "gamePrice": game["pricePerPaperGame"], "sales": {GamePaper.SOLD: 0, GamePaper.ON_SALE: 0}})
        if game["gamePaperStatus"] == GamePaper.SOLD:
            sale_type["sales"][GamePaper.SOLD] = sale_type["sales"][GamePaper.SOLD] + game["sum"]
        elif game["gamePaperStatus"] == GamePaper.ON_SALE:
            sale_type["sales"][GamePaper.ON_SALE] = sale_type["sales"][GamePaper.ON_SALE] + game["sum"]
    return sales

def removeBatch(gameUniqueId):
    game = GameType.get_or_none(GameType.gameUniqueId==gameUniqueId)
    if game is None:
        return False
    else:
        game.delete_instance(recursive=True)
        return True

def addBatch(gameUniqueId, gameBatchId):
    game = GameType.get_or_none(GameType.gameUniqueId==gameUniqueId)
    current_stock = None
    with db.atomic() as _:
        gamePaper = GamePaper.get_or_none(GamePaper.gameUniqueId==gameUniqueId, GamePaper.gameBatchId==gameBatchId)
        # we should only register a new batch if is new
        if gamePaper is None:
            if game is None:
                game = registerNewGame(gameUniqueId)
                out = f"Current stock [{game.numberOfGamesPerBatch}]: "
                current_stock = input(out)
            registerNewBatch(game, gameBatchId, current_stock=current_stock)
        else:
            print("Batch already registered!")

def sellGamePaper(gameUniqueId, gameBatchId):
    gamePaper = GamePaper.get_or_none(GamePaper.gameUniqueId==gameUniqueId, GamePaper.gameBatchId==gameBatchId, GamePaper.gamePaperStatus==GamePaper.ON_SALE)
    if gamePaper is None:
        return False
    else:
        gamePaper.gamePaperStatus = GamePaper.SOLD
        gamePaper.gameSoldAt = datetime.now(tz=timezone.utc)
        gamePaper.save()
        return True

def inputProcessor(userInput):
    global mode
    if userInput.isnumeric():
        if len(userInput) == 10:
            gameUniqueId = userInput[0:3]
            gameBatchId = userInput[3:]
            if mode=="sell":
                if not sellGamePaper(gameUniqueId, gameBatchId):
                    print("Game is not register or there are no more Paper to sell!")
            elif mode=="add_batch":
                addBatch(gameUniqueId, gameBatchId)
            elif mode=="remove_batch":
                removeBatch(gameUniqueId)
                if not removeBatch(gameUniqueId):
                    print("Batch is not register!")
        else:
            print("Unknown format!")
    else:
        if userInput == "sell":
            mode = "sell"
        elif userInput == "add_batch":
            mode = "add_batch"
        elif userInput == "remove_batch":
            mode = "remove_batch"
        elif userInput == "report":
            from_date = dateparser.parse(input("Since: ") or datetime(2000,1,1).isoformat())
            to_date = dateparser.parse(input("To: ") or datetime.now(tz=timezone.utc).isoformat())
            print("From: ", from_date)
            print("To: ", to_date)
            for sale in createSaleReport(to_date, from_date).values():
                print(sale["gameName"])
                print("\t", "Remains: ", sale["sales"][GamePaper.ON_SALE])
                print("\t", "Sold: ", sale["sales"][GamePaper.SOLD])
                print("\t", "Money: ", sale["sales"][GamePaper.SOLD] * sale["gamePrice"], " €")
        elif userInput == "show_all_games":
            for game in GameType.select().dicts():
                print(game)
        elif userInput == "show_all_papers":
            for paper in GamePaper.select().dicts():
                print(paper)
        elif userInput == "exit":
            exit()


def main():
    global mode
    while True:
        try:
            out = f"Current mode {mode}\n"
            command = input(out)
            inputProcessor(command)
        except Exception:
            pass

if __name__ == "__main__":
    main()


