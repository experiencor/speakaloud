CREATE TABLE IF NOT EXISTS event (
	id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    session_id VARCHAR(32),
    paragraph_id INT,
    word_index INT,
    start_time TIMESTAMP(6) default CURRENT_TIMESTAMP(6)
);

CREATE TABLE IF NOT EXISTS user (    
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) default "",
    email VARCHAR(64) default "",
    password VARCHAR(64) default "",
    age INT default 0,
    country VARCHAR(64) default "",
    created_at TIMESTAMP default CURRENT_TIMESTAMP,
    INDEX(name, email)
);

CREATE TABLE IF NOT EXISTS paragraph (
	id INT AUTO_INCREMENT PRIMARY KEY,
    text VARCHAR(1024)
);

INSERT INTO paragraph (text) VALUES ("We must reuse the plastic bags we already have at home as many times as we can before throwing them away.");

INSERT INTO paragraph (text) VALUES ("Good writers accomplish these tasks by immediately establishing each paragraph’s topic and maintaining paragraph unity, by using concrete, personal examples to demonstrate their points, and by not prolonging the ending of the essay needlessly.");

INSERT INTO paragraph (text) VALUES ("Looking for houses was supposed to be a fun and exciting process.");

INSERT INTO user (age, country) VALUES (24, "vietnam");

