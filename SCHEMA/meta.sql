CREATE TABLE `meta` (
  id integer PRIMARY KEY,
  skrap_id integer,
  k varchar(64) NOT NULL,
  v blob,
  UNIQUE(skrap_id, k),
  FOREIGN KEY(skrap_id) REFERENCES skrap(id)
);

