from bot import card
from enums import Value


class CardKnowledge(card.Card):
    def __init__(self, bot, player, deckPosition, suit, rank):
        super().__init__(bot.game, player, deckPosition, suit, rank)
        self.bot = bot
        self.cantBe = {c: [False] * 6 for c in self.bot.colors}
        self.color = None
        self.value = None
        self.playable = None
        self.valuable = None
        self.worthless = None
        self.cluedAsDiscard = False
        self.cluedAsClarify = False
        self.cluedAsSingle = False
        self.clued = False

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        result.cantBe = {c: self.cantBe[c][:] for c in self.bot.colors}
        return result

    def mustBeColor(self, color):
        return color == self.color

    def mustBeValue(self, value):
        return value == self.value

    def cannotBeColor(self, color):
        if self.color is not None:
            return self.color != color
        for v in self.bot.values:
            if not self.cantBe[color][v]:
                return False
        return True

    def cannotBeValue(self, value):
        if self.value is not None:
            return self.value != value
        for c in self.bot.colors:
            if not self.cantBe[c][value]:
                return False
        return True

    def setMustBeColor(self, color):
        tot = 0
        for c in self.bot.colors:
            if c == color:
                continue
            tot += self.setCannotBeColor(c)
        self.color = color
        return tot

    def setMustBeValue(self, value):
        tot = 0
        for v in self.bot.values:
            if v == value:
                continue
            tot += self.setCannotBeValue(v)
        self.value = value
        return tot

    def setCannotBeColor(self, color):
        tot = 0
        for v in self.bot.values:
            if not self.cantBe[color][v]:
                tot += 1
                self.cantBe[color][v] = True
        return tot

    def setCannotBeValue(self, value):
        tot = 0
        for c in self.bot.colors:
            if not self.cantBe[c][value]:
                tot += 1
                self.cantBe[c][value] = True
        return tot

    def setIsPlayable(self, knownPlayable):
        for c in self.bot.colors:
            playableValue = len(self.bot.game.playedCards[c]) + 1
            for v in self.bot.values:
                if self.cantBe[c][v]:
                    continue
                if (v == playableValue) != knownPlayable:
                    self.cantBe[c][v] = True
        self.playable = knownPlayable

    def setIsValuable(self, knownValuable):
        for c in self.bot.colors:
            for v in self.bot.values:
                if self.cantBe[c][v]:
                    continue
                if self.bot.isValuable(c, v) != knownValuable:
                    self.cantBe[c][v] = True
        self.playable = knownValuable

    def setIsWorthless(self, knownWorthless):
        for c in self.bot.colors:
            for v in self.bot.values:
                if self.cantBe[c][v]:
                    continue
                if self.bot.isWorthless(c, v) != knownWorthless:
                    self.cantBe[c][v] = True
        self.worthless = knownWorthless

    def update(self, useMyEyesight):
        if useMyEyesight:
            self.update_count(useMyEyesight)
        else:
            self.update_valid_canbe(useMyEyesight)

        if self.color is not None and self.value is not None:
            score = len(self.game.playedCards[self.color])
            self.setIsPlayable(score + 1 == self.value)
            self.setIsWorthless(
                self.value <= len(self.game.playedCards[self.color])
                or self.value > self.bot.maxPlayValue[self.color])
        elif self.color is not None:
            if self.bot.colorComplete[self.color]:
                self.setIsWorthless(True)
            if self.bot.colorComplete[self.color]:
                self.setIsWorthless(True)
        elif self.value is not None:
            self.worthless = self.value < self.bot.lowestPlayableValue
            if self.value == self.bot.lowestPlayableValue:
                self.playable = True
        if self.canBePlayable():
            self.playable = True
            self.setIsWorthless(None)

        self.valuable = None

        if self.worthless is True:
            self.valuable = False
            self.playable = False

    def canBePlayable(self):
        if self.worthless:
            return False
        if self.value is not None:
            if self.value == Value.V5:
                for c in self.bot.colors:
                    if self.cantBe[c][5]:
                        continue
                    if len(self.game.playedCards[c]) != 4:
                        return False
                return True
        elif self.color is not None:
            if self.cluedAsSingle:
                score = len(self.game.playedCards[self.color])
                for i in self.bot.hand:
                    if i == self.deckPosition:
                        continue
                    card = self.game.deck[i]
                    if card.color == self.color and card.value == score + 1:
                        return False
        if self.cluedAsSingle:
            return True
        return False

    def update_valid_canbe(self, useMyEyesight):
        color = self.color
        if color is None:
            for c in self.bot.colors:
                if self.cannotBeColor(c):
                    continue
                elif color is None:
                    color = c
                else:
                    color = None
                    break
            if color is not None:
                self.setMustBeColor(color)

        value = self.value
        if value is None:
            for v in self.bot.values:
                if self.cannotBeValue(v):
                    continue
                elif value is None:
                    value = v
                else:
                    value = None
                    break
            if value is not None:
                self.setMustBeValue(value)

        assert color == self.color
        assert value == self.value
        assert (self.color is None or self.suit is None
                or self.suit == self.color), (self.suit, self.color)
        assert (self.value is None or self.rank is None
                or self.rank == self.value), (self.rank, self.value)

        self.update_count(useMyEyesight)

    def update_count(self, useMyEyesight):
        if self.color is None or self.value is None:
            restart = False
            for c in self.bot.colors:
                for v in self.bot.values:
                    if self.cantBe[c][v]:
                        continue
                    total = v.num_copies
                    played = self.bot.playedCount[c][v]
                    if useMyEyesight:
                        held = self.bot.eyeSightCount[c][v]
                    else:
                        held = self.bot.locatedCount[c][v]
                    assert played + held <= total
                    if played + held == total:
                        self.cantBe[c][v] = True
                        restart = True
            if restart:
                self.update_valid_canbe(useMyEyesight)
