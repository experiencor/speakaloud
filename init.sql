CREATE TABLE IF NOT EXISTS event (
    id INT AUTO_INCREMENT       PRIMARY KEY,
    user_id INT                 NOT NULL,
    paragraph_id INT            NOT NULL,
    session_id VARCHAR(32)      NOT NULL,
    word_index INT              NOT NULL,
    word VARCHAR(32)            NOT NULL,
    paragraph_length INT        NOT NULL,
    duration INT                NOT NULL,
    completed_at INT            NOT NULL,
    created_at TIMESTAMP(6)     DEFAULT CURRENT_TIMESTAMP(6)
);

CREATE TABLE IF NOT EXISTS final_sent (
    id INT AUTO_INCREMENT       PRIMARY KEY,
    user_id INT                 NOT NULL,
    paragraph_id INT            NOT NULL,
    session_id VARCHAR(32)      NOT NULL,
    sentence VARCHAR(1024)      NOT NULL,
    word_index INT              NOT NULL,
    word VARCHAR(32)            NOT NULL,    
    started_at INT            	NOT NULL,
    completed_at INT            NOT NULL,   
    created_at TIMESTAMP(6)     DEFAULT CURRENT_TIMESTAMP(6)
);

CREATE TABLE IF NOT EXISTS user (    
    id INT AUTO_INCREMENT   PRIMARY KEY,
    username VARCHAR(32)    DEFAULT "",
    email VARCHAR(64)       DEFAULT "",
    fullname VARCHAR(64)    DEFAULT "",
    password VARCHAR(64)    DEFAULT "",
    level INT               DEFAULT 0,
    next_paragraph_id INT   DEFAULT 1,
    age INT                 DEFAULT 0,
    country VARCHAR(64)     DEFAULT "",
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX(username, email)
);
	
CREATE TABLE IF NOT EXISTS paragraph (
    id INT AUTO_INCREMENT   PRIMARY KEY,
    topic VARCHAR(64)       DEFAULT "",
    tags VARCHAR(256)       DEFAULT "",
    source VARCHAR(64)      DEFAULT "",
    author VARCHAR(64)      DEFAULT "",
    level INT               DEFAULT 0,
    length INT              DEFAULT -1,
    content VARCHAR(1024)   DEFAULT "",
    ipa VARCHAR(1024)       DEFAULT "",
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE user        ADD level   INT         DEFAULT 1;
ALTER TABLE paragraph   ADD level   INT         DEFAULT 1;
ALTER TABLE paragraph   ADD source  VARCHAR(64) DEFAULT "";
ALTER TABLE paragraph   ADD author  VARCHAR(64) DEFAULT "";

INSERT INTO paragraph (content) VALUES ("We must reuse the plastic bags we already have at home as many times as we can before throwing them away.");
INSERT INTO paragraph (content) VALUES ("Good writers accomplish these tasks by immediately establishing each paragraph’s topic and maintaining paragraph unity, by using concrete, personal examples to demonstrate their points, and by not prolonging the ending of the essay needlessly.");
INSERT INTO paragraph (content) VALUES ("Looking for houses was supposed to be a fun and exciting process.");
INSERT INTO paragraph (content) VALUES ("I mostly like to read biographies. I'm not sure why but it is interesting to read about people's real lives, especially when they have had interesting lives and have had to deal with many problems. I do read fiction as well, but I often find it difficult to get hold of a book that I really like. I also like reading about books to do with current affairs.");
INSERT INTO paragraph (content) VALUES ("Not really, no. Actually I didn't read that much when I was a child, but if I did it was mainly fiction books, such as fairy tales. Things like The Lion, The Witch, and the Wardrobe. Fantasy things.");
INSERT INTO paragraph (content) VALUES ("I think any time is ok, but when I read I like to concentrate, so I can't read for a short time like on a bus ride like some people do. I like to put time aside to enjoy it. So if I have some free time at the weekend I might read for a few hours. And I nearly always read before I go to bed - this really helps me to sleep.");
INSERT INTO paragraph (content) VALUES ("No, not that I know of. I live in a small town so I don't think there are any, though we do have a few museums and other cultural institutions. In our capital city there are quite a few art galleries, however.");
INSERT INTO paragraph (content) VALUES ("I've never been that interested in art to be honest, so not really. We were taken to one as part of a trip when I was at school. It has a lot of paintings from famous artists from our country. It was quite interesting to see I guess but I've not been to any since.");
INSERT INTO paragraph (content) VALUES ("I think it depends really. If possible they should be free because if people do have to pay they are less likely to go and see it. But on the other hand these things cost money so a small fee may be necessary if it can keep the art gallery going and keep it open. Ideally though the government should pay for this as I believe this kind of thing is paid for by our taxes.");
INSERT INTO paragraph (content) VALUES ("Yes I can. I learnt at school when I was about 7 years old. Swimming lessons were compulsory at our school, like most schools I think.");
INSERT INTO paragraph (content) VALUES ("Yes, there are a few public swimming pools. There is the main indoor one at a big sports complex in the center of town. There are also a couple of outdoor ones, but you can only use them in summer as it is too cold in winter. One is a big one in a park, the other is a much smaller one.");
INSERT INTO paragraph (content) VALUES ("Of course, I think it's very important. Firstly, you spend much of your life on holiday by water, for example, when you go to the beach on holiday, so you won't be able to enjoy yourself with your friends if you can't swim. Also, for safety reasons it's very important. You often hear about sad accidents involving young children so it's very important.");
INSERT INTO paragraph (content) VALUES ("Although technology is a good thing, everything has two sides. Technology also has two sides one is good and the other is bad. Here are some negative aspects of technology that we are going to discuss.");
INSERT INTO paragraph (content) VALUES ("I asked God for a bike, but I know God doesn’t work that way. So I stole a bike and asked for forgiveness.");
INSERT INTO paragraph (content) VALUES ("Light travels faster than sound. This is why some people appear bright until you hear them speak.");
INSERT INTO paragraph (content) VALUES ("Do not argue with an idiot. He will drag you down to his level and beat you with experience.");
INSERT INTO paragraph (content) VALUES ("The problem isn’t that obesity runs in your family. The problem is no one runs in your family.");
INSERT INTO paragraph (content) VALUES ("In my picture, the umbrella's red and white. In my picture, the man isn't wearing sunglasses. In my picture, there are three steps.");
INSERT INTO paragraph (content) VALUES ("Give a man a fish and you feed him for a day. But teach a man to fish, and you saved yourself a fish, haven't you");
INSERT INTO paragraph (content) VALUES ("A positive attitude may not solve all your problems. But it will annoy enough people to make it worth the effort.");
INSERT INTO paragraph (content) VALUES ("Today a man knocked on my door and asked for a small donation toward the local swimming pool. I gave him a glass of water.");
INSERT INTO paragraph (content) VALUES ("I am 3 years old.");
INSERT INTO paragraph (content) VALUES ("Hello. My name is Laura.");
INSERT INTO paragraph (content) VALUES ("Nevertheless, there are drawbacks to such a solution. First and foremost, this would be a heavy burden on the car drivers. At present, taxes are already high for a lot of people, and so further taxes would only mean less money at the end of the month for most people who may have no choice but to drive every day. In addition, this type of tax would likely be set at a fixed amount. This would mean that it would hit those with less money harder, whilst the rich could likely afford it. It is therefore not a fair tax.");

INSERT INTO user (age, next_paragraph_id, country) VALUES (24, 1, "vietnam");