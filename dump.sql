SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection=utf8mb4;

START TRANSACTION;

DROP TABLE IF EXISTS user_consents;
CREATE TABLE user_consents (
    user_id BIGINT PRIMARY KEY,
    data_consent TINYINT(1) NOT NULL,
    offer_consent TINYINT(1) NOT NULL,
    timestamp DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS messages;
CREATE TABLE messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    text TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO messages VALUES
(1,'Начать','КУРС: ВЫКУП ЗЕМЛИ\n\nЭтот курс - готовая система, где вы получите пошаговый план действий по стратегии: «Выкуп земли из аренды с торгов», которая позволяет выкупать землю у государства по минимальной стоимости, с выгодой до 80 процентов ниже рыночной стоимости по сравнению с ценами на Авито. [Работает не во всех регионах, проверить свой]\n\nИ ГЛАВНЫЙ БОНУС «Стратегия перепродажи участков с открытого рынка»\nЭто отдельная технология, как прямо с открытого рынка, без торгов, находить, улучшать и перепродавать участки с наценкой до 50%! [Работает во всех регионах]\n\nКурс это целая система в формате закрытого Telegram-канала проверенная на практике. Все материалы всегда у вас под рукой, в телефоне, и вы можете изучать их в любое удобное время: в пробке, в обеденный перерыв, где угодно.\n\nЯ делюсь только теми методами, которые многократно проверены на практике.\n\nВаша задача — брать и делать. '),
(2,'Подробнее','Курс это целая система в формате закрытого Telegram-канала проверенная на практике. Все материалы всегда у вас под рукой, в телефоне, и вы можете изучать их в любое удобное время: в пробке, в обеденный перерыв, где угодно.\n\nВнутри вас ждут:\n\nВидео\nПрезентации\nПолезные посты с советами экспертов\nРазборы кейсов\nЧат с единомышленниками\nПрочие бонусы\n\nЭтот курс идеально подойдет вам, если вы:\n\nХотите выгодно покупать землю для себя или перепродажи.\nРиэлтор или юрист, нацеленный на расширение компетенций.\nГотовы действовать и нужен четкий план для быстрого заработка на земле.\n\n\nВы узнаете:\n\nКак учавствовать в торгах и выкупать землю из аренды с выгодой до 80 процентов ниже рыночной стоимости\nКак находить самые перспективные участки, которые будут востребованы.\nКак проводить анализ земли и понимать ее реальную ценность и ликвидность.\nПроверять на юридические ограничения и риски.\nГрамотно готовить землю к продаже, чтобы увеличить её стоимость.\nКакие инструменты использовать для продвижения и поиска покупателей.\nКак оптимизировать налоги, чтобы максимизировать свою прибыль.\n\nАвтор курса – Ларин Андрей, не просто теоретик, а предприниматель и действующий кадастровый инженер с высшим землеустроительным образованием. Вот уже более 11 лет я успешно работаю в сфере недвижимости и помог сотням моих клиентов успешно оформить в собственность сотни гектаров земли по всей стране для самых разных целей: от коммерческих проектов до строительства частных домов. При этом я не просто консультант — я сам инвестор: строю дома, владею десятками гектаров и постоянно нахожу новые инвестиционные возможности.'),
(4,'Купить','Оплатив доступ, вы мгновенно получите приглашение в закрытое сообщество. \n\nТам всё готово для вашего успешного старта: вас ждут подробные материалы и пошаговое руководство по выкупу земли по минимальной стоимости и заработку на недвижимости.\n\nВаш доступ ко всем этим сокровищам действует 1 год. Дальнейшие условия продления – на усмотрение автора.'),
(6,'Согласие на обработку данных','Перед покупкой необходимо согласиться с обработкой персональных данных и акцептовать оферту.\n\nПодтвердите согласие, нажав на кнопки ниже:');

DROP TABLE IF EXISTS reviews;
CREATE TABLE reviews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    photo_url VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS support_tickets;
CREATE TABLE support_tickets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    username VARCHAR(255),
    full_name VARCHAR(255),
    question TEXT NOT NULL,
    status VARCHAR(255) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    registration_date DATETIME,
    registration_timestamp BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO users VALUES
(820368286,'Trustmemate','Mate',NULL,NULL,'2025-08-13 17:10:05',1755094205);

DROP TABLE IF EXISTS user_links;
CREATE TABLE user_links (
    user_id BIGINT PRIMARY KEY,
    invite_link VARCHAR(255),
    created_at BIGINT,
    created_date DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS payments;
CREATE TABLE payments (
    user_id BIGINT,
    payment_id VARCHAR(255),
    amount FLOAT,
    currency VARCHAR(10),
    payment_timestamp BIGINT,
    payment_date DATETIME,
    payment_method VARCHAR(50),
    payment_status VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, payment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO payments VALUES
(123456789,'test_payment_123',1000.0,'RUB',1755162819,'2025-08-14 12:13:39','unknown','succeeded'),
(123456891,'test_payment_12',1000.0,'RUB',1755163307,'2025-08-14 12:21:47','unknown','succeeded');

COMMIT;
